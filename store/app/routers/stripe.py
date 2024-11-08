"""Stripe integration router for handling payments and webhooks."""

import logging
from typing import Annotated, Any, Dict

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from store.app.db import Crud
from store.app.model import Order, User
from store.app.routers.users import get_session_user_with_read_permission
from store.settings import settings

logger = logging.getLogger(__name__)

stripe_router = APIRouter()

# Initialize Stripe with your secret key
stripe.api_key = settings.stripe.secret_key


@stripe_router.post("/create-payment-intent")
async def create_payment_intent(request: Request) -> Dict[str, Any]:
    try:
        data = await request.json()
        amount = data.get("amount")

        # Create a PaymentIntent with the order amount and currency
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency="usd",
            automatic_payment_methods={
                "enabled": True,
            },
        )

        return {"clientSecret": intent.client_secret}
    except Exception as e:
        return {"error": str(e)}


class CancelReason(BaseModel):
    reason: str
    details: str


class CreateRefundsRequest(BaseModel):
    payment_intent_id: str
    cancel_reason: CancelReason
    amount: int


@stripe_router.put("/refunds/{order_id}", response_model=Order)
async def refund_payment_intent(
    order_id: str,
    refund_request: CreateRefundsRequest,
    user: User = Depends(get_session_user_with_read_permission),
    crud: Crud = Depends(),
) -> Order:
    async with crud:
        try:
            amount = refund_request.amount
            payment_intent_id = refund_request.payment_intent_id
            customer_reason = (
                refund_request.cancel_reason.details
                if (refund_request.cancel_reason.reason == "Other" and refund_request.cancel_reason.details)
                else refund_request.cancel_reason.reason
            )

            # Create a Refund for payment_intent_id with the order amount
            refund = stripe.Refund.create(
                payment_intent=payment_intent_id,
                amount=amount,
                reason="requested_by_customer",
                metadata={"customer_reason": customer_reason},
            )
            logger.info("Refund created: %s", refund.id)

            # Make sure order exists
            order = await crud.get_order(order_id)
            if order is None or order.user_id != user.id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
            logger.info("Found order id: %s", order.id)

            # Update order status
            order_data = {
                "stripe_refund_id": refund.id,
                "status": (
                    "refunded" if (refund.status and refund.status) == "succeeded" else (refund.status or "no status!")
                ),
            }

            updated_order = await crud.update_order(order_id, order_data)

            logger.info("Updated order with status: %s", refund.status)
            return updated_order
        except Exception as e:
            logger.error("Error processing refund: %s", str(e))
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@stripe_router.post("/webhook")
async def stripe_webhook(request: Request, crud: Crud = Depends(Crud.get)) -> Dict[str, str]:
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    logger.info("Received Stripe webhook. Signature: %s", sig_header)

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.stripe.webhook_secret)
        logger.info("Webhook verified. Event type: %s", event["type"])
    except ValueError as e:
        logger.error("Invalid payload: %s", str(e))
        raise HTTPException(status_code=400, detail="Invalid payload")

    # Handle the event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        logger.info("Checkout session completed: %s", session["id"])
        await handle_checkout_session_completed(session, crud)
    elif event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        logger.info("Payment intent succeeded: %s", payment_intent["id"])
    else:
        logger.info("Unhandled event type: %s", event["type"])

    return {"status": "success"}


async def handle_checkout_session_completed(session: Dict[str, Any], crud: Crud) -> None:
    try:
        shipping_details = session.get("shipping_details", {})
        shipping_address = shipping_details.get("address", {})

        # Get the line items to extract the quantity
        line_items = stripe.checkout.Session.list_line_items(session["id"])
        quantity = line_items.data[0].quantity if line_items.data else 1

        order_data = {
            "user_id": session.get("client_reference_id"),
            "user_email": session["customer_details"]["email"],
            "stripe_checkout_session_id": session["id"],
            "stripe_payment_intent_id": session.get("payment_intent"),
            "amount": session["amount_total"],
            "currency": session["currency"],
            "status": "processing",
            "product_id": session["metadata"].get("product_id"),
            "quantity": quantity,
            "shipping_name": shipping_details.get("name"),
            "shipping_address_line1": shipping_address.get("line1"),
            "shipping_address_line2": shipping_address.get("line2"),
            "shipping_city": shipping_address.get("city"),
            "shipping_state": shipping_address.get("state"),
            "shipping_postal_code": shipping_address.get("postal_code"),
            "shipping_country": shipping_address.get("country"),
        }

        new_order = await crud.create_order(order_data)
        logger.info("New order created: %s", new_order.id)
    except Exception as e:
        logger.error("Error creating order: %s", str(e))
        raise


async def fulfill_order(
    session: Dict[str, Any],
    crud: Annotated[Crud, Depends(Crud.get)],
) -> None:
    user_id = session.get("client_reference_id")
    if not user_id:
        logger.warning("No user_id found for session: %s", session["id"])
        return

    user = await crud.get_user(user_id)
    if not user:
        logger.warning("User not found for id: %s", user_id)
        return

    order_data = {
        "user_id": user_id,
        "stripe_checkout_session_id": session["id"],
        "stripe_payment_intent_id": session["payment_intent"],
        "amount": session["amount_total"],
        "currency": session["currency"],
        "status": "processing",
        "product_id": session["metadata"].get("product_id"),
        "user_email": session["metadata"].get("user_email"),
    }

    try:
        await crud.create_order(order_data)
        logger.info("Order fulfilled for session: %s and user: %s", session["id"], user_id)
    except Exception as e:
        logger.error("Error creating order: %s", str(e))
        # You might want to add some error handling here, such as retrying or notifying an admin


async def notify_payment_failed(session: Dict[str, Any]) -> None:
    logger.warning("Payment failed for session: %s", session["id"])


class CreateCheckoutSessionRequest(BaseModel):
    product_id: str
    cancel_url: str


class CreateCheckoutSessionResponse(BaseModel):
    session_id: str


@stripe_router.post("/create-checkout-session", response_model=CreateCheckoutSessionResponse)
async def create_checkout_session(
    request: CreateCheckoutSessionRequest,
    user: Annotated[User, Depends(get_session_user_with_read_permission)],
) -> CreateCheckoutSessionResponse:
    try:
        product_id = request.product_id
        cancel_url = request.cancel_url
        logger.info("Creating checkout session for product: %s and user: %s", product_id, user.id)

        # Fetch the price associated with the product
        prices = stripe.Price.list(product=product_id, active=True, limit=1)
        if not prices.data:
            raise HTTPException(status_code=400, detail="No active price found for this product")
        price = prices.data[0]

        # Create a Checkout Session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card", "affirm"],
            line_items=[
                {
                    "price": price.id,
                    "quantity": 1,
                    "adjustable_quantity": {
                        "enabled": True,
                        "minimum": 1,
                        "maximum": 10,
                    },
                }
            ],
            automatic_tax={"enabled": True},
            mode="payment",
            success_url=f"{settings.site.homepage}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.site.homepage}{cancel_url}",
            client_reference_id=user.id,
            metadata={
                "product_id": product_id,
                "user_email": user.email,
            },
            shipping_address_collection={
                "allowed_countries": ["US", "CA"],
            },
            currency="usd",
            shipping_options=[
                {
                    "shipping_rate_data": {
                        "type": "fixed_amount",
                        "fixed_amount": {"amount": 0, "currency": "usd"},
                        "display_name": "Free shipping",
                        "delivery_estimate": {
                            "minimum": {"unit": "business_day", "value": 5},
                            "maximum": {"unit": "business_day", "value": 7},
                        },
                    },
                },
                {
                    "shipping_rate_data": {
                        "type": "fixed_amount",
                        "fixed_amount": {"amount": 2500, "currency": "usd"},
                        "display_name": "Ground - Express",
                        "delivery_estimate": {
                            "minimum": {"unit": "business_day", "value": 2},
                            "maximum": {"unit": "business_day", "value": 5},
                        },
                    },
                },
            ],
        )

        logger.info("Checkout session created: %s", checkout_session.id)
        return CreateCheckoutSessionResponse(session_id=checkout_session.id)
    except Exception as e:
        logger.error("Error creating checkout session: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e))


@stripe_router.get("/get-product/{product_id}")
async def get_product(product_id: str) -> Dict[str, Any]:
    try:
        product = stripe.Product.retrieve(product_id)
        return {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "images": product.images,
            "metadata": product.metadata,
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
