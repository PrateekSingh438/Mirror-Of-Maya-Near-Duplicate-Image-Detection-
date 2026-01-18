# Mirror of Maya - Setup Guide

This guide will help you set up and run both the Python backend API and the React frontend.

## Prerequisites

- Python 3.10+
- Node.js 18+ and npm
- CUDA-capable GPU (recommended) or CPU

## Backend Setup

1. **Activate your virtual environment** (if using venv):
```bash
# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

2. **Install Python dependencies** (if not already installed):
```bash
pip install -r requirements.txt
pip install fastapi uvicorn python-multipart networkx
```

3. **Start the FastAPI backend server**:
```bash
python api_server.py
```

The API will be available at `http://localhost:8000`

## Frontend Setup

1. **Navigate to the frontend directory**:
```bash
cd frontend
```

2. **Install dependencies**:
```bash
npm install
```

3. **Start the development server**:
```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`

**Note:** The frontend uses JavaScript with SWC (a fast Rust-based compiler) instead of TypeScript for improved performance.

## Using the Application

1. **Start both servers**:
   - Backend: `python api_server.py` (port 8000)
   - Frontend: `npm run dev` (port 5173)

2. **Configure Settings**:
   - Open `http://localhost:5173` in your browser
   - In the sidebar, set the dataset path (e.g., `./dataset_copydays`)
   - Adjust the similarity threshold (default: 82%)
   - Select a model (DINOv2 Small recommended for best F1 score)

3. **Scan for Duplicates**:
   - Click "Fresh Scan" in the sidebar
   - Wait for the scan to complete
   - View results in the Dashboard tab

4. **Explore Features**:
   - **Dashboard**: Overview metrics and quick stats
   - **Metrics & Report**: Detailed analytics with charts
   - **Galaxy Clusters**: Visualize and manage duplicate clusters
   - **Query Tool**: Upload an image to find its duplicates

## API Endpoints

The FastAPI backend exposes the following endpoints:

- `GET /api/health` - Health check
- `POST /api/scan` - Scan dataset for duplicates
- `GET /api/duplicates` - Get duplicate pairs (paginated)
- `GET /api/clusters` - Get duplicate clusters (paginated)
- `POST /api/search` - Search for similar images (upload file)
- `GET /api/metrics` - Get analytics and metrics
- `POST /api/delete` - Delete selected files
- `GET /api/models` - Get available models
- `GET /images` - Serve images from dataset

## Project Structure

```
Mirror-Of-Maya-Near-Duplicate-Image-Detection-/
├── api_server.py          # FastAPI backend
├── engine.py              # Core duplicate detection engine
├── app.py                 # Original Streamlit app (legacy)
├── frontend/              # React frontend
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── services/      # API client
│   │   └── App.tsx        # Main app
│   └── package.json
└── dataset_copydays/      # Dataset directory
```

## Troubleshooting

1. **CORS errors**: Make sure the backend is running on port 8000
2. **Images not loading**: Verify the `/images` endpoint in the backend
3. **API connection errors**: Check that both servers are running
4. **Module not found**: Install missing dependencies with `pip install` or `npm install`

## Production Build

To build the frontend for production:

```bash
cd frontend
npm run build
```

The built files will be in `frontend/dist/`. You can serve them with any static file server or integrate with the FastAPI backend.

## Notes

- The frontend uses a proxy to communicate with the backend API
- Images are served through the `/images` endpoint for security
- The Maya theme uses a purple and gold color scheme inspired by Sudarshana Chakra
- All API calls are made through the `apiService` in `frontend/src/services/api.ts`

