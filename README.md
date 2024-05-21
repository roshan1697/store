# store

This is the code for our online store. This is a simple store for buying and selling humanoid robots.

## Development

To develop the application, start FastAPI and React in separate terminals:

### FastAPI

Serve the FastAPI application in development mode:

```bash
fastapi dev 'store/app/main.py'
```

### React

Automatically rebuild the React frontend code when a file is changed:

```bash
cd frontend
nvm use 20.10.0  # If you're using nvm
npm install  # If you haven't already
npm run watch
```