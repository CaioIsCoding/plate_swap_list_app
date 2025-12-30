import React from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { GripVertical, Clock, Weight, X } from 'lucide-react';
import { cn } from '../lib/utils';

export function PlateCard({ item, index, onRemove, onUpdateCount }) {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging
    } = useSortable({ id: item.id });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        zIndex: isDragging ? 10 : 1,
    };

    const formatTime = (seconds) => {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        return `${h}h ${m}m ${s}s`;
    };

    const handleCountChange = (e) => {
        const val = parseInt(e.target.value);
        if (val > 0) onUpdateCount(item.id, val);
    };

    return (
        <div
            ref={setNodeRef}
            style={style}
            className={cn(
                "relative flex flex-col w-64 bg-gray-200 rounded-lg shadow-md border  group overflow-hidden",
                isDragging ? "opacity-50 border-blue-500" : "border-gray-300"
            )}
        >
            {/* Header / ID */}
            <div className="flex items-center justify-between px-3 py-1 bg-gray-300/50">
                <span className="font-bold text-gray-500 text-lg">{index + 1}</span>
                <div className="flex items-center gap-2">
                    {/* Drag Handle */}
                    <div {...attributes} {...listeners} className="cursor-grab hover:text-blue-600">
                        <GripVertical size={18} />
                    </div>
                    {/* Remove Button */}
                    <button onClick={() => onRemove(item.id)} className="text-gray-400 hover:text-red-500">
                        <X size={18} />
                    </button>
                </div>
            </div>

            {/* Thumbnail */}
            <div className="relative aspect-square bg-white m-2 rounded-md overflow-hidden flex items-center justify-center">
                {item.image_url ? (
                    <img src={`http://127.0.0.1:8000${item.image_url}`} alt="Plate" className="object-contain w-full h-full" />
                ) : (
                    <div className="text-gray-400">No Image</div>
                )}
            </div>

            {/* Info */}
            <div className="p-3 bg-gray-200 text-sm grid grid-cols-2 gap-2 items-center">
                <div className="flex items-center gap-1 text-gray-700">
                    <Clock size={14} />
                    <span>{item.print_time ? formatTime(item.print_time) : "--"}</span>
                </div>

                <div className="flex justify-end">
                    <input
                        type="number"
                        min="1"
                        value={item.count}
                        onChange={handleCountChange}
                        className="w-12 px-1 py-0.5 border border-gray-400 rounded text-center bg-white"
                    />
                </div>

                <div className="flex items-center gap-1 text-gray-700 col-span-2">
                    <Weight size={14} />
                    <span>{item.weight ? item.weight.toFixed(2) : "0"}g</span>
                </div>
            </div>

            {/* Filename Overlay (like reference) */}
            <div className="absolute top-8 left-3 text-xs text-gray-600 font-medium truncate max-w-[80%]">
                {item.filename || "Unknown"}
            </div>
        </div>
    );
}
