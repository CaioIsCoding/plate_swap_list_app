import os
import sys
import shutil
import tempfile
import uuid

# Add parent directory to path to import generate_swap_gcode
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_swap_gcode import extract_3mf_to_temp, process_3mf_playlist
import xml.etree.ElementTree as ET

TEMP_STORAGE = tempfile.gettempdir()
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

def parse_3mf(file_path):
    """
    Parses a 3MF file and returns a list of plates with metadata.
    """
    # Extract to temp
    extract_dir = extract_3mf_to_temp(file_path)
    metadata_dir = os.path.join(extract_dir, "Metadata")
    
    plates = []
    
    # We need to return info for the UI:
    # - Thumbnail URL (we need to serve this)
    # - Plate Index
    # - Weight / Time
    
    if os.path.exists(metadata_dir):
        # Find slice_info
        slice_info_path = os.path.join(metadata_dir, "slice_info.config")
        stats_map = {} # index -> {weight, time}
        
        if os.path.exists(slice_info_path):
            try:
                tree = ET.parse(slice_info_path)
                root = tree.getroot()
                for plate in root.findall('plate'):
                    idx_meta = plate.find("metadata[@key='index']")
                    idx = idx_meta.get('value') if idx_meta is not None else "1"
                    
                    weight_meta = plate.find("metadata[@key='weight']")
                    pred_meta = plate.find("metadata[@key='prediction']")
                    
                    stats_map[idx] = {
                        "weight": float(weight_meta.get('value', 0)) if weight_meta is not None else 0,
                        "time": int(pred_meta.get('value', 0)) if pred_meta is not None else 0
                    }
            except Exception as e:
                print(f"Error parsing slice_info: {e}")

        # List plates
        for f in os.listdir(metadata_dir):
            if f.startswith("plate_") and f.endswith(".png"):
                # Found a plate thumbnail -> valid plate
                # plate_1.png -> index 1
                # STRICT match to avoid matching 'plate_1_small.png'
                import re
                match = re.search(r"^plate_(\d+)\.png$", f)
                if match:
                    idx = match.group(1)
                    
                    # Copy thumbnail to STATIC_DIR
                    if not os.path.exists(STATIC_DIR):
                        os.makedirs(STATIC_DIR)
                        
                    unique_img_name = f"thumb_{uuid.uuid4().hex[:8]}_{f}"
                    dst_img_path = os.path.join(STATIC_DIR, unique_img_name)
                    shutil.copy(os.path.join(metadata_dir, f), dst_img_path)
                    
                    # Public URL
                    image_url = f"/static/{unique_img_name}"
                    
                    stats = stats_map.get(idx, {"weight": 0, "time": 0})
                    
                    plates.append({
                        "id": str(uuid.uuid4()),
                        "filename": os.path.basename(file_path),
                        "file_path": file_path, # Keep track of where the source 3mf is (temp)
                        "plate_index": int(idx),
                        "image_url": image_url, # Now a URL
                        "weight": stats['weight'],
                        "print_time": stats['time']
                    })
    
    return plates

def generate_swap_file(playlist_items):
    """
    Generates the swap file from the playlist items.
    """
    # Convert UI playlist items to (path, index, count) tuple
    playlist = []
    for item in playlist_items:
        # item has 'file_path' (source temp 3mf), 'plate_index', 'count'
        playlist.append((item.file_path, item.plate_index, item.count))
        
    output_filename = f"swap_playlist_{uuid.uuid4().hex[:8]}.3mf"
    
    if not os.path.exists(STATIC_DIR):
        os.makedirs(STATIC_DIR)
        
    output_path = os.path.join(STATIC_DIR, output_filename)
    
    process_3mf_playlist(playlist, output_path)
    
    # Return relative URL for download
    return f"/static/{output_filename}"

