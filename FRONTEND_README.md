# Mirror of Maya - Frontend

A beautiful, Maya-themed React frontend for the Near-Duplicate Image Detection system, built with Vite and TypeScript.

## Features

- 🎨 **Elegant Maya Theme**: Sudarshana Chakra-inspired design with mystical aesthetics
- 📊 **Interactive Dashboard**: Real-time metrics and performance visualization
- 🔍 **Query Tool**: Upload images to find duplicates using the Sudarshana Chakra search
- 🌌 **Galaxy Clusters**: Visualize and manage duplicate image clusters
- 📈 **Detailed Metrics**: Comprehensive analysis with charts and graphs

## Prerequisites

- Node.js 18+ and npm
- Python backend server running on port 8000 (see `api_server.py`)

## Installation

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`

## Building for Production

```bash
npm run build
```

The built files will be in the `dist` directory.

## Project Structure

```
frontend/
├── src/
│   ├── components/      # React components
│   │   ├── Header.tsx   # Top navigation with Chakra icon
│   │   ├── Sidebar.tsx  # Settings and scan controls
│   │   ├── Dashboard.tsx # Main overview
│   │   ├── MetricsView.tsx # Detailed metrics
│   │   ├── ClustersView.tsx # Galaxy clusters visualization
│   │   └── QueryTool.tsx # Image search tool
│   ├── services/        # API service layer
│   │   └── api.ts       # API client
│   ├── App.tsx          # Main app component
│   ├── main.tsx         # Entry point
│   └── index.css        # Global styles
├── public/              # Static assets
└── package.json         # Dependencies
```

## API Integration

The frontend communicates with the FastAPI backend at `http://localhost:8000/api`. The Vite proxy configuration handles CORS automatically.

## Styling

The app uses a custom Maya-themed color palette:
- Primary Purple: `#8B4E9E`
- Secondary Purple: `#C9A6D4`
- Gold Accent: `#FFD700`
- Dark Background: `#1A0D1F`

## Components

### Header
Displays the app title with a rotating Sudarshana Chakra icon.

### Sidebar
- Model selection
- Dataset path configuration
- Similarity threshold slider
- Scan button

### Dashboard
Shows overview metrics:
- Total storage
- Potential savings
- Duplicate pairs
- F1 score

### Metrics View
Detailed analysis with:
- Storage pie chart
- Match type analysis
- Performance metrics

### Clusters View
- Browse duplicate clusters
- Select files for deletion
- Paginated navigation

### Query Tool
- Drag-and-drop image upload
- Real-time duplicate search
- Results grid with similarity scores

## Development

The project uses:
- **React 18** with TypeScript
- **Vite** for fast development
- **Recharts** for data visualization
- **Lucide React** for icons
- **Axios** for API calls

## Troubleshooting

1. **CORS errors**: Ensure the backend is running and CORS is configured
2. **Images not loading**: Check the `/images` endpoint in the backend
3. **API errors**: Verify the backend is running on port 8000

## Next Steps

- Add authentication
- Implement real-time updates via WebSocket
- Add more visualization options
- Improve image loading performance

