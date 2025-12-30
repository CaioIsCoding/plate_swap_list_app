import os
import shutil
import hashlib
import xml.etree.ElementTree as ET
import zipfile
import tempfile
import re

# --- CONSTANTS ---

SWAP_INIT_GCODE = """;swap ini code
G91 ; 
G0 Z50 F1000; 
G0 Z-20; 
G90; 
 G28 XY; 
 G0 Y-4 F5000; grab 
 G0 Y145;  pull and fix the plate
G0 Y115 F1000; rehook 
 G0 Y180 F5000; pull
 G4 P500; wait  
 G0 Y186.5 F200; fix the plate
 G4 P500; wait  
 G0 Y3 F15000; back 
 G0 Y-5 F200; snap 
G4 P500; wait  
 G0 Y10 F1000; load 
 G0 Y20 F15000; ready 
 
"""

SWAP_SEQUENCE_GCODE = """;swap 
G0 X-10 F5000; 
 G0 Z175; 
 G0 Y-5 F2000;  
  G0 Y186.5 F2000;  
  G0 Y182 F10000;  
  G0 Z186 ; 
 G0 Y120 F500; 
 G0 Y-4 Z175 F5000; 
 G0 Y145; 
  G0 Y115 F1000; 
 G0 Y25 F500; 
 G0 Y85 F1000; 
 G0 Y180 F2000; 
 G4 P500; wait  
 G0 Y186.5 F200; 
 G4 P500; wait  
 G0 Y3 F3000; 
 G0 Y-5 F200; 
G4 P500; wait  
 G0 Y10 F1000; 
 G0 Z100 Y186 F2000; 
 G0 Y150; 
 G4 P1000; wait  
 
"""

# --- HELPER FUNCTIONS ---

def get_metadata_dir(gcode_path):
    """Returns the parent directory of a G-code file."""
    return os.path.dirname(os.path.abspath(gcode_path))

def calculate_md5(file_path):
    """Calculates the MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def merge_slice_info(playlist, output_config_path):
    """
    Merges slice_info.config from all items in the playlist.
    Aggregates stats (weight, time, lengths) and combines unique filaments.
    """
    
    total_prediction = 0
    total_weight = 0.0
    found_index_1_stats = False
    merged_filaments = {} # Key: id (or type+color), Value: Filament Element (accumulated)
    
    # We need a base XML structure. We'll start fresh or use the first valid one.
    base_tree = None
    base_root = None
    
    print("Merging slice_info.config data...")

    import re

    for gcode_path, count in playlist:
        src_dir = get_metadata_dir(gcode_path)
        config_path = os.path.join(src_dir, "slice_info.config")
        
        if not os.path.exists(config_path):
            print(f"Warning: No slice_info.config found for {gcode_path}")
            continue
            
        tree = ET.parse(config_path)
        root = tree.getroot()
        
        # Identify the plate index from filename (e.g. plate_1.gcode -> 1)
        filename = os.path.basename(gcode_path)
        match = re.search(r"plate_(\d+)", filename)
        target_index = match.group(1) if match else None
        
        if base_tree is None:
            # We must parse a fresh copy for the base template so we don't modify 'tree' which we need to read from!
            base_tree = ET.parse(config_path)
            base_root = base_tree.getroot()
            
            # Ensure we start with a CLEAN single plate structure
            # Remove all existing plates except the first one
            plates = base_root.findall('plate')
            for i, p in enumerate(plates):
                if i > 0:
                    base_root.remove(p)
            
            target_plate = base_root.find('plate')
            if target_plate is None:
                base_tree = None 
                continue
                
            # Clear filaments to rebuild
            for fil in target_plate.findall('filament'):
                target_plate.remove(fil)
            
            # Force Index to 1 (Swap file convention)
            for meta in target_plate.findall('metadata'):
                if meta.get('key') == 'index':
                    meta.set('value', '1')
                
        # Iterate through plates in the config
        # If we have a target_index, we ONLY process that plate.
        
        found_plate = False
        
        for plate in root.findall('plate'):
            # Check index metadata
            plate_index = None
            for meta in plate.findall('metadata'):
                if meta.get('key') == 'index':
                    plate_index = meta.get('value')
                    break
            
            if target_index and plate_index and target_index != plate_index:
                continue # Skip non-matching plates
            
            found_plate = True
            
            # --- UPDATE: Header Stats Logic ---
            # The reference file 'Metadata - Inverted + More Prints' shows that even if Plate 2 is printed first,
            # the slice_info header statistics (Prediction/Weight) reflect Plate 1 (Index 1).
            # So, we should prioritize Metadata from Plate 1.
            
            # Logic:
            # - If this plate is Index 1, we captures its stats as the Authority.
            # - If we haven't found an Authority yet, we take the First Plate's stats as a fallback.
            # - Overwrite fallback if we find Plate 1 later.
            
            prediction = 0
            weight = 0.0
            
            for meta in plate.findall('metadata'):
                key = meta.get('key')
                val = meta.get('value')
                if key == 'prediction':
                    prediction = int(val)
                elif key == 'weight':
                    weight = float(val)
            
            # Capture if:
            # 1. We have nothing yet (Fallback to first item).
            # 2. OR This is Plate 1 (Index 1), which overrides any fallback.
            
            is_index_1 = (plate_index == '1')
            
            if total_weight == 0.0:
                total_prediction = prediction
                total_weight = weight
                if is_index_1:
                    found_index_1_stats = True
            elif is_index_1 and not found_index_1_stats:
                # Found Plate 1 later in the playlist, override!
                total_prediction = prediction
                total_weight = weight
                found_index_1_stats = True
            
            # Process filaments (Always Sum)
            for filament in plate.findall('filament'):
                f_id = filament.get('id')
                f_type = filament.get('type')
                f_color = filament.get('color')
                
                key = f_id
                
                used_m = float(filament.get('used_m', 0.0)) * count
                used_g = float(filament.get('used_g', 0.0)) * count
                
                if key not in merged_filaments:
                    new_el = ET.Element('filament')
                    new_el.set('id', f_id)
                    new_el.set('type', f_type)
                    new_el.set('color', f_color)
                    if filament.get('tray_info_idx'):
                        new_el.set('tray_info_idx', filament.get('tray_info_idx'))
                        
                    new_el.set('used_m', str(used_m))
                    new_el.set('used_g', str(used_g))
                    merged_filaments[key] = new_el
                else:
                    current_el = merged_filaments[key]
                    cur_m = float(current_el.get('used_m'))
                    cur_g = float(current_el.get('used_g'))
                    
                    current_el.set('used_m', f"{cur_m + used_m:.2f}")
                    current_el.set('used_g', f"{cur_g + used_g:.2f}")

        if not found_plate:
            print(f"Warning: Could not match plate index {target_index} in config for {filename}")
    
    # Write back to Base Tree
    if base_tree is None:
        print("Error: Could not parse any slice_info.config files.")
        return

    target_plate = base_root.find('plate')
    
    # Update Metadata (Prediction/Weight)
    found_pred = False
    found_weight = False
    
    for meta in target_plate.findall('metadata'):
        key = meta.get('key')
        if key == 'prediction':
            meta.set('value', str(total_prediction))
            found_pred = True
        elif key == 'weight':
            meta.set('value', f"{total_weight:.2f}")
            found_weight = True
            
    if not found_pred:
        wm = ET.SubElement(target_plate, 'metadata')
        wm.set('key', 'prediction')
        wm.set('value', str(total_prediction))
        
    if not found_weight:
        wm = ET.SubElement(target_plate, 'metadata')
        wm.set('key', 'weight')
        wm.set('value', f"{total_weight:.2f}")

    # Append Merged Filaments
    # Sort by ID for consistency
    sorted_keys = sorted(merged_filaments.keys(), key=lambda x: int(x) if x.isdigit() else x)
    
    for k in sorted_keys:
        target_plate.append(merged_filaments[k])

    # Save
    base_tree.write(output_config_path, encoding='UTF-8', xml_declaration=True)
    print(f"Updated slice_info.config: {total_weight:.2f}g (First Plate), Matches Reference Behavior.")


def copy_assets(playlist, output_dir):
    """
    Copies relevant assets (PNG, JSON, MD5) from valid source directories.
    Handles filename collisions if necessary, but for now we trust the structure (plate_1, plate_2 etc).
    """
    processed_files = set()
    
    print("Copying assets from source directories...")
    
    # We want to ensure we copy the model_settings.config from the FIRST item as a base template if possible,
    # or rely on `update_model_settings` to fix it later.
    # But strictly, we copy images/jsons/md5s.
    
    first_dir = None
    
    for gcode_path, _ in playlist:
        src_dir = get_metadata_dir(gcode_path)
        if first_dir is None: 
            first_dir = src_dir
        
        # Determine the basename of the gcode to identify related files
        # e.g. "plate_1.gcode" -> we look for "plate_1.*"
        basename = os.path.basename(gcode_path)
        rootname = os.path.splitext(basename)[0] # "plate_1"
        
        for item in os.listdir(src_dir):
            if item.startswith(rootname) or item.startswith("pick_") or item.startswith("top_") or item.startswith("model_settings"):
                # We copy:
                # 1. Matches "plate_X.*" (png, json, md5)
                # 2. "pick_X.png", "top_X.png"
                # 3. "model_settings.config" (we might overwrite this multiple times, effectively taking the last one? 
                #    Better to take the first one or merge. We'll take first one implicitly if we check for existence,
                #    OR overwrite. Let's overwrite to ensure we have *some* settings.)
                
                # SKIP gcode files themselves (we generate one)
                if item.endswith(".gcode"):
                    continue
                
                # SKIP slice_info (we generate/merge it)
                if item == "slice_info.config":
                    continue

                src_file = os.path.join(src_dir, item)
                dst_file = os.path.join(output_dir, item)
                
                # If file exists, should we overwrite?
                # If we have plate_1.png from dir A and plate_1.png from dir B... collision.
                # Assumption: Playlist usually combines DIFFERENT plates (plate_1 + plate_2).
                # If combining plate_1 (A) + plate_1 (B), we might have issues.
                # User's case: Metadata - 2 Objects has plate_1 and plate_2 in ONE dir.
                # So no collision.
                
                shutil.copy2(src_file, dst_file)
    
    # Also copy project_settings and other globals from the FIRST directory encountered
    if first_dir:
        for item in os.listdir(first_dir):
             if item == "project_settings.config" or item.startswith("filament_settings"):
                 s = os.path.join(first_dir, item)
                 d = os.path.join(output_dir, item)
                 if not os.path.exists(d):
                     shutil.copy2(s, d)

    print("Assets copied.")

def generate_swap_gcode_content(playlist):
    """
    Generates the content of the combined G-code file using internal templates.
    """
    gcode_content = []
    gcode_content.append(SWAP_INIT_GCODE)
    
    total_items = 0
    for obj_path, count in playlist:
        if not os.path.exists(obj_path):
            print(f"Warning: File not found: {obj_path}, skipping.")
            continue
        
        print(f"Processing {count} copies of: {os.path.basename(obj_path)}")
        
        with open(obj_path, 'r', encoding='utf-8') as obj_f:
            obj_content = obj_f.read()
        
        for i in range(count):
            gcode_content.append(obj_content)
            if not obj_content.endswith('\n'):
                gcode_content.append('\n')
            
            gcode_content.append(SWAP_SEQUENCE_GCODE)
            if not SWAP_SEQUENCE_GCODE.endswith('\n'):
                gcode_content.append('\n')
            
            total_items += 1
            
    return "".join(gcode_content)


def update_model_settings(config_path):
    """
    Updates the model_settings.config to identify as a Swap plate.
    Sets 'plater_name' to 'SWAP'.
    Removes extra plates and specific metadata keys to match reference structure.
    """
    if not os.path.exists(config_path):
        return

    tree = ET.parse(config_path)
    root = tree.getroot()
    
    # 1. Keep only the first plate
    plates = root.findall('plate')
    for i, p in enumerate(plates):
        if i > 0:
            root.remove(p)
            
    plate = root.find('plate')
    
    if plate is not None:
        # 2. Update plater_name
        found_name = False
        for meta in plate.findall('metadata'):
            key = meta.get('key')
            
            if key == 'plater_name':
                meta.set('value', 'SWAP')
                found_name = True
                
        if not found_name:
             new_meta = ET.SubElement(plate, 'metadata')
             new_meta.set('key', 'plater_name')
             new_meta.set('value', 'SWAP')

        # 3. Remove unwanted keys
        # Keys to remove based on diff: filament_map_mode, filament_maps, thumbnail_no_light_file
        keys_to_remove = ['filament_map_mode', 'filament_maps', 'thumbnail_no_light_file', 'locked']
        
        # We must collect elements to remove first to avoid modifying iterator
        to_remove = []
        for meta in plate.findall('metadata'):
            if meta.get('key') in keys_to_remove:
                to_remove.append(meta)
        
        for item in to_remove:
            plate.remove(item)
             
    tree.write(config_path, encoding='UTF-8', xml_declaration=True)

def create_swap_metadata(playlist, output_dir):
    """
    Creates the complete Swap Metadata folder.
    """
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)
    
    print(f"Created output directory: {output_dir}")

    # 1. Copy Assets
    copy_assets(playlist, output_dir)

    # 2. Generate Combined G-code
    output_gcode_path = os.path.join(output_dir, "plate_1.gcode")
    gcode_content = generate_swap_gcode_content(playlist)
    
    with open(output_gcode_path, 'w', encoding='utf-8') as f:
        f.write(gcode_content)
    
    print(f"Generated combined G-code at {output_gcode_path}")

    # 3. Generate MD5 for the new G-code
    md5_hash = calculate_md5(output_gcode_path)
    with open(output_gcode_path + ".md5", 'w', encoding='utf-8') as f:
        f.write(md5_hash)
    print("Generated MD5 checksum.")

    # 4. Update model_settings.config
    output_model_settings = os.path.join(output_dir, "model_settings.config")
    update_model_settings(output_model_settings)

    # 5. Merge slice_info.config
    output_slice_info = os.path.join(output_dir, "slice_info.config")
    merge_slice_info(playlist, output_slice_info)

# --- 3MF SUPPORT ---

def extract_3mf_to_temp(threemf_path):
    """
    Extracts a 3MF file to a temporary directory and returns the path.
    """
    temp_dir = tempfile.mkdtemp(prefix="swap_extract_")
    with zipfile.ZipFile(threemf_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    return temp_dir

def zip_directory(folder_path, output_path):
    """
    Zips the contents of a folder into a standard zip file (renamed to .3mf).
    """
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                # Archive name should be relative to folder_path
                arcname = os.path.relpath(file_path, folder_path)
                zipf.write(file_path, arcname)

def process_3mf_playlist(playlist_3mf, output_3mf_path):
    """
    Process a playlist of 3MF files.
    playlist_3mf: List of tuples (threemf_path, plate_index_or_none, count)
    output_3mf_path: Path to write the final 3MF.
    """
    
    # 1. Setup Staging for Base Container
    # We use the FIRST 3MF in the playlist as the base container for models/settings.
    if not playlist_3mf:
        print("Error: Empty playlist.")
        return
        
    first_3mf_path = playlist_3mf[0][0]
    base_staging_dir = extract_3mf_to_temp(first_3mf_path)
    print(f"Base 3MF extracted to: {base_staging_dir}")
    
    # Prepare Metadata target in Base Staging
    base_metadata_dir = os.path.join(base_staging_dir, "Metadata")
    if os.path.exists(base_metadata_dir):
        shutil.rmtree(base_metadata_dir) # Clear existing metadata
    os.makedirs(base_metadata_dir)
    
    # 2. Extract Inputs and Build G-code Playlist
    gcode_playlist = []
    temp_dirs = [base_staging_dir] # Keep track to clean up later
    
    print("Extracting inputs...")
    for threemf_path, target_plate_idx, count in playlist_3mf:
        # Extract to new temp
        extract_dir = extract_3mf_to_temp(threemf_path)
        temp_dirs.append(extract_dir)
        
        metadata_dir = os.path.join(extract_dir, "Metadata")
        if not os.path.exists(metadata_dir):
            print(f"Warning: No Metadata folder in {threemf_path}")
            continue
            
        # Find G-codes
        # If target_plate_idx is specified, look for 'plate_{idx}.gcode'
        # Else, look for ALL 'plate_*.gcode' and sort them.
        
        found_gcodes = []
        
        if target_plate_idx:
            target_name = f"plate_{target_plate_idx}.gcode"
            p = os.path.join(metadata_dir, target_name)
            if os.path.exists(p):
                found_gcodes.append(p)
            else:
                print(f"Warning: Plate {target_plate_idx} not found in {threemf_path}")
        else:
            # All plates
            files = os.listdir(metadata_dir)
            files = [f for f in files if f.startswith("plate_") and f.endswith(".gcode")]
            # Sort by index
            files.sort(key=lambda x: int(re.search(r"plate_(\d+)", x).group(1)) if re.search(r"plate_(\d+)", x) else 999)
            found_gcodes = [os.path.join(metadata_dir, f) for f in files]
            
        # Add to playlist
        for gp in found_gcodes:
            gcode_playlist.append((gp, count))
            
    # 3. Generate Swap Metadata into Base Staging
    print(f"Generating Swap Metadata into {base_metadata_dir}...")
    
    # Reuse existing logic!
    # Note: create_swap_metadata handles clearing the dir, but we just made it.
    # It calls copy_assets -> generate_gcode -> update_configs.
    # This matches our needs exactly.
    create_swap_metadata(gcode_playlist, base_metadata_dir)
    
    # 4. Repackage
    print(f"Repackaging to {output_3mf_path}...")
    zip_directory(base_staging_dir, output_3mf_path)
    
    # 5. Cleanup
    print("Cleaning up temporary directories...")
    for d in temp_dirs:
        shutil.rmtree(d)
        
    print("3MF Processing Complete.")

if __name__ == "__main__":
    BASE_DIR = "/Users/caio/Downloads/swaplist app"
    
    # --- TEST RUN 1: Combined 2 Objects ---
    print("\n>>> RUNNING TEST 1: 2 Objects (Plate 1 + Plate 2) <<<")
    DIR_2_OBJS = os.path.join(BASE_DIR, "Metadata - 2 Objects")
    OUTPUT_DIR_2 = os.path.join(BASE_DIR, "Metadata - Swap Generated 2 Objects")
    
    PLAYLIST_2 = [
        (os.path.join(DIR_2_OBJS, "plate_1.gcode"), 1),
        (os.path.join(DIR_2_OBJS, "plate_2.gcode"), 1),
    ]
    create_swap_metadata(PLAYLIST_2, OUTPUT_DIR_2)
    
    # --- TEST RUN 2: Original (2 Copies) ---
    print("\n>>> RUNNING TEST 2: Original (2 Copies) <<<")
    DIR_ORIG = os.path.join(BASE_DIR, "Metadata - Original")
    OUTPUT_DIR_ORIG = os.path.join(BASE_DIR, "Metadata - Swap Generated Original")
    
    PLAYLIST_ORIG = [
        (os.path.join(DIR_ORIG, "plate_1.gcode"), 2),
    ]
    create_swap_metadata(PLAYLIST_ORIG, OUTPUT_DIR_ORIG)
    
    # --- TEST RUN 3: Inverted + More Prints ---
    print("\n>>> RUNNING TEST 3: Inverted (Plate 2 x2, Plate 1 x3) <<<")
    # Source is 'Metadata - 2 Objects' because the user said they used the objects FROM there.
    # The 'Metadata - Inverted...' folder is likely the reference result.
    
    OUTPUT_DIR_INV = os.path.join(BASE_DIR, "Metadata - Swap Generated Inverted")
    
    PLAYLIST_INV = [
        (os.path.join(DIR_2_OBJS, "plate_2.gcode"), 2),
        (os.path.join(DIR_2_OBJS, "plate_1.gcode"), 3),
    ]
    create_swap_metadata(PLAYLIST_INV, OUTPUT_DIR_INV)

    print("\n---------------------------------------------------")
    print(f"SUCCESS! Generated test folders:\n1. {OUTPUT_DIR_2}\n2. {OUTPUT_DIR_ORIG}\n3. {OUTPUT_DIR_INV}")
    print("---------------------------------------------------")

    # --- TEST RUN 4: 3MF Support ---
    print("\n>>> RUNNING TEST 4: 3MF Support (2 Objects.3mf -> Inverted) <<<")
    INPUT_3MF = os.path.join(BASE_DIR, "2 Objects.3mf")
    OUTPUT_3MF = os.path.join(BASE_DIR, "generated_swap_playlist.3mf")
    
    # Playlist: (3MF Path, Plate Index, Count)
    # We want Plate 2 (1 copy) then Plate 1 (1 copy)
    PLAYLIST_3MF = [
        (INPUT_3MF, 2, 1),
        (INPUT_3MF, 1, 1)
    ]
    
    process_3mf_playlist(PLAYLIST_3MF, OUTPUT_3MF)
    print(f"SUCCESS! Generated 3MF at: {OUTPUT_3MF}")
