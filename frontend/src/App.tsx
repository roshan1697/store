import { Route, BrowserRouter as Router, Routes } from "react-router-dom";

import "@/App.css";

import Container from "@/components/Container";
import NotFoundRedirect from "@/components/NotFoundRedirect";
import PendoInitializer from "@/components/PendoInitializer";
import { ScrollToTop } from "@/components/ScrollToTop";
import SprigInitializer from "@/components/SprigInitializer";
import Footer from "@/components/footer/Footer";
import { FeaturedListingsProvider } from "@/components/listing/FeaturedListings";
import Navbar from "@/components/nav/Navbar";
import APIKeys from "@/components/pages/APIKeys";
import About from "@/components/pages/About";
import Account from "@/components/pages/Account";
import Browse from "@/components/pages/Browse";
import Create from "@/components/pages/Create";
import EmailSignup from "@/components/pages/EmailSignup";
import FileBrowser from "@/components/pages/FileBrowser";
import Home from "@/components/pages/Home";
import Listing from "@/components/pages/Listing";
import Login from "@/components/pages/Login";
import Logout from "@/components/pages/Logout";
import NotFound from "@/components/pages/NotFound";
import Profile from "@/components/pages/Profile";
import SellerDashboard from "@/components/pages/SellerDashboard";
import Signup from "@/components/pages/Signup";
import { AlertQueue, AlertQueueProvider } from "@/hooks/useAlertQueue";
import { AuthenticationProvider } from "@/hooks/useAuth";

import GDPRBanner from "./components/gdpr/gdprbanner";
import DeleteConnect from "./components/pages/DeleteConnect";
import DownloadsPage from "./components/pages/Download";
import OrderSuccess from "./components/pages/OrderSuccess";
import OrdersPage from "./components/pages/Orders";
import Playground from "./components/pages/Playground";
import PrivacyPolicy from "./components/pages/PrivacyPolicy";
import ResearchPage from "./components/pages/ResearchPage";
import SellerOnboarding from "./components/pages/SellerOnboarding";
import Terminal from "./components/pages/Terminal";
import TermsOfService from "./components/pages/TermsOfService";

const App = () => {
  return (
    <Router>
      <AuthenticationProvider>
        <FeaturedListingsProvider>
          <AlertQueueProvider>
            <AlertQueue>
              <ScrollToTop>
                <div className="flex flex-col bg-gray-1 text-gray-12 min-h-screen">
                  <Navbar />
                  <GDPRBanner />
                  <PendoInitializer />
                  <SprigInitializer />
                  <div className="flex-grow">
                    <Container>
                      <Routes>
                        <Route path="/" element={<Home />} />

                        <Route path="/playground" element={<Playground />} />

                        <Route path="/about" element={<About />} />
                        <Route path="/downloads" element={<DownloadsPage />} />
                        <Route path="/research" element={<ResearchPage />} />
                        <Route path="/browse/:page?" element={<Browse />} />
                        <Route
                          path="/file/:artifactId"
                          element={<FileBrowser />}
                        />
                        <Route path="/account" element={<Account />} />
                        <Route path="/login" element={<Login />} />
                        <Route path="/logout" element={<Logout />} />
                        <Route path="/signup/" element={<Signup />} />
                        <Route path="/signup/:id" element={<EmailSignup />} />

                        <Route path="/create" element={<Create />} />
                        <Route
                          path="/item/:username/:slug"
                          element={<Listing />}
                        />
                        <Route path="/keys" element={<APIKeys />} />
                        <Route path="/profile/:id?" element={<Profile />} />

                        <Route path="/tos" element={<TermsOfService />} />
                        <Route path="/privacy" element={<PrivacyPolicy />} />

                        <Route
                          path="/sell/onboarding"
                          element={<SellerOnboarding />}
                        />
                        <Route
                          path="/sell/dashboard"
                          element={<SellerDashboard />}
                        />
                        <Route
                          path="/delete-connect"
                          element={<DeleteConnect />}
                        />

                        <Route path="/success" element={<OrderSuccess />} />
                        <Route path="/orders" element={<OrdersPage />} />

                        <Route path="/terminal" element={<Terminal />} />
                        <Route path="/terminal/:id" element={<Terminal />} />

                        <Route path="/404" element={<NotFound />} />
                        <Route path="*" element={<NotFoundRedirect />} />
                      </Routes>
                    </Container>
                  </div>
                  <Footer />
                </div>
              </ScrollToTop>
            </AlertQueue>
          </AlertQueueProvider>
        </FeaturedListingsProvider>
      </AuthenticationProvider>
    </Router>
  );
};

export default App;
