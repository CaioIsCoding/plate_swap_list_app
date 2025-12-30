import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { UploadCloud } from 'lucide-react';
import { cn } from '../lib/utils';

export function Dropzone({ onDropFiles, uploading }) {
    const onDrop = useCallback(acceptedFiles => {
        if (acceptedFiles?.length > 0) {
            onDropFiles(acceptedFiles);
        }
    }, [onDropFiles]);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            'model/3mf': ['.3mf', '.gcode'],
            'application/octet-stream': ['.3mf', '.gcode']
        }
    });

    return (
        <div
            {...getRootProps()}
            className={cn(
                "w-full h-32 border-2 border-dashed rounded-lg flex flex-col items-center justify-center cursor-pointer transition-colors",
                "border-blue-300 bg-blue-50/50 hover:bg-blue-100/50",
                isDragActive && "border-blue-500 bg-blue-100",
                uploading && "opacity-50 pointer-events-none"
            )}
        >
            <input {...getInputProps()} />
            <div className="text-center text-blue-400 font-bold text-lg uppercase">
                {uploading ? "Processing..." : (isDragActive ? "Drop here!" : "Drop your file(s) here")}
            </div>
            <div className="text-blue-300 text-sm mt-1 italic">
                ...or click to select
            </div>
        </div>
    );
}
