import React, { useState } from 'react';
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { arrayMove, SortableContext, sortableKeyboardCoordinates, rectSortingStrategy } from '@dnd-kit/sortable';
import axios from 'axios';
import { PlateCard } from './components/PlateCard';
import { Dropzone } from './components/Dropzone';
import { Download, RefreshCcw, Loader2 } from 'lucide-react';

const API_BASE = "http://127.0.0.1:8000/api";

function App() {
  const [playlist, setPlaylist] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [generating, setGenerating] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const handleDropFiles = async (files) => {
    setUploading(true);
    try {
      const newItems = [];
      for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);

        const res = await axios.post(`${API_BASE}/upload`, formData);
        if (res.data.plates) {
          newItems.push(...res.data.plates);
        }
      }

      // Add default count and ensure IDs are unique if same file added twice? 
      // Backend returns generic IDs.
      setPlaylist(prev => [...prev, ...newItems.map(p => ({ ...p, count: 1 }))]);
    } catch (err) {
      console.error("Upload failed", err);
      alert("Failed to upload file");
    } finally {
      setUploading(false);
    }
  };

  const handleDragEnd = (event) => {
    const { active, over } = event;
    if (active.id !== over.id) {
      setPlaylist((items) => {
        const oldIndex = items.findIndex((i) => i.id === active.id);
        const newIndex = items.findIndex((i) => i.id === over.id);
        return arrayMove(items, oldIndex, newIndex);
      });
    }
  };

  const removeItem = (id) => {
    setPlaylist(items => items.filter(i => i.id !== id));
  };

  const updateCount = (id, count) => {
    setPlaylist(items => items.map(i => i.id === id ? { ...i, count } : i));
  };

  const handleReset = () => {
    if (confirm("Clear playlist?")) {
      setPlaylist([]);
    }
  };

  const handleGenerate = async () => {
    if (playlist.length === 0) return;
    setGenerating(true);
    try {
      const payload = { playlist };
      const res = await axios.post(`${API_BASE}/generate`, payload);
      if (res.data.download_url) {
        const url = `http://127.0.0.1:8000${res.data.download_url}`;
        window.open(url, '_blank');
      }
    } catch (err) {
      console.error("Generate failed", err);
      alert("Failed to generate swap file");
    } finally {
      setGenerating(false);
    }
  };

  // Stats
  const totalDuration = playlist.reduce((acc, item) => acc + (item.print_time * item.count), 0);
  const totalWeight = playlist.reduce((acc, item) => acc + (item.weight * item.count), 0);
  const totalPlates = playlist.reduce((acc, item) => acc + item.count, 0);

  const formatTime = (seconds) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return `${h}h ${m}m`;
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col font-sans text-gray-800">
      {/* Top Bar */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-gray-800">
            swaplist<span className="text-yellow-400">.app</span>
          </h1>

          <div className="mt-4 flex gap-8 text-sm">
            <div>
              <span className="font-bold block text-gray-600">Queue statistics:</span>
              <div className="grid grid-cols-[auto_1fr] gap-x-2 mt-1">
                <span>Duration:</span>
                <span className="font-bold">{formatTime(totalDuration)}</span>
                <span>Plates:</span>
                <span className="font-bold">{totalPlates}</span>
              </div>
            </div>

            <div>
              <span className="font-bold block text-gray-600">Weight statistics:</span>
              <div className="mt-1">
                <span>Total: </span>
                <span className="font-bold">{totalWeight.toFixed(2)}g</span>
              </div>
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-2 items-end">
          <button
            onClick={handleReset}
            className="bg-gray-600 hover:bg-gray-700 text-white py-1 px-4 rounded text-sm flex items-center gap-2"
          >
            <RefreshCcw size={14} /> Reset
          </button>

          <button
            onClick={handleGenerate}
            disabled={playlist.length === 0 || generating}
            className="bg-yellow-300 hover:bg-yellow-400 text-black font-bold py-2 px-6 rounded shadow-sm flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {generating ? <Loader2 className="animate-spin" /> : <Download size={18} />}
            Generate SWAP file
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-6 max-w-7xl mx-auto w-full flex flex-col gap-6">
        <Dropzone onDropFiles={handleDropFiles} uploading={uploading} />

        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext
            items={playlist.map(p => p.id)}
            strategy={rectSortingStrategy}
          >
            <div className="flex flex-wrap gap-4">
              {playlist.map((item, idx) => (
                <PlateCard
                  key={item.id}
                  item={item}
                  index={idx}
                  onRemove={removeItem}
                  onUpdateCount={updateCount}
                />
              ))}
            </div>
          </SortableContext>
        </DndContext>

        {playlist.length === 0 && !uploading && (
          <div className="text-center text-gray-400 mt-10">
            No plates yet. Drop a file to start.
          </div>
        )}
      </div>

      <div className="text-center text-xs text-gray-400 py-4">
        Local SwapList Generator
      </div>
    </div>
  );
}

export default App;
