"""
Diagnostic script to verify your dataset structure
Run this BEFORE using the main application
"""
import os
from collections import defaultdict

DATASET_PATH = "./dataset_copydays"
SUPPORTED_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.webp', '.tiff')

def analyze_dataset(path):
    print("=" * 60)
    print("DATASET STRUCTURE ANALYSIS")
    print("=" * 60)
    
    if not os.path.exists(path):
        print(f"❌ ERROR: Path does not exist: {path}")
        return
    
    print(f"✓ Dataset path exists: {path}\n")
    
    # Collect all image files
    all_files = []
    for root, _, files in os.walk(path):
        for f in files:
            if f.lower().endswith(SUPPORTED_EXTENSIONS):
                full_path = os.path.join(root, f)
                all_files.append(full_path)
    
    print(f"📊 Total images found: {len(all_files)}\n")
    
    if len(all_files) == 0:
        print("❌ No images found!")
        return
    
    # Analyze directory structure
    dir_structure = defaultdict(list)
    for f in all_files:
        rel_path = os.path.relpath(f, path)
        parts = rel_path.split(os.sep)
        
        if len(parts) >= 2:
            folder = parts[0]
            dir_structure[folder].append(f)
    
    print("📁 Directory breakdown:")
    for folder, files in sorted(dir_structure.items()):
        print(f"   {folder}/: {len(files)} files")
    print()
    
    # Check for 'original' folder
    has_original = any('original' in f.lower() for f in all_files)
    
    if has_original:
        print("✓ Found 'original' folder")
        original_files = [f for f in all_files if 'original' in f.lower()]
        print(f"  → {len(original_files)} original images")
        
        # Show samples
        print("\n  Sample original files:")
        for f in original_files[:5]:
            print(f"    • {os.path.basename(f)}")
    else:
        print("⚠️  WARNING: No 'original' folder found!")
        print("   Expected structure:")
        print("   dataset_copydays/")
        print("   ├── original/")
        print("   │   ├── image1.jpg")
        print("   │   └── image2.jpg")
        print("   └── attacks/ (or strong/, weak/, etc.)")
    
    print("\n" + "=" * 60)
    print("BASENAME ANALYSIS (for ground truth pairing)")
    print("=" * 60)
    
    # Group by basename
    basename_groups = defaultdict(list)
    for f in all_files:
        basename = os.path.splitext(os.path.basename(f))[0]
        basename_groups[basename].append(f)
    
    # Find basenames with multiple instances
    duplicates_by_name = {k: v for k, v in basename_groups.items() if len(v) > 1}
    
    print(f"\n📝 Unique basenames: {len(basename_groups)}")
    print(f"📝 Basenames with duplicates: {len(duplicates_by_name)}")
    
    if len(duplicates_by_name) > 0:
        print("\n✓ Sample duplicate groups (for ground truth):")
        for i, (basename, files) in enumerate(list(duplicates_by_name.items())[:3]):
            print(f"\n  Group {i+1}: '{basename}'")
            for f in files:
                is_orig = 'original' in f.lower()
                marker = "📌 ORIGINAL" if is_orig else "   attack"
                print(f"    {marker}: {os.path.relpath(f, path)}")
        
        # Count expected ground truth pairs
        expected_pairs = 0
        for basename, files in duplicates_by_name.items():
            originals = [f for f in files if 'original' in f.lower()]
            attacks = [f for f in files if 'original' not in f.lower()]
            expected_pairs += len(originals) * len(attacks)
        
        print(f"\n📊 Expected ground truth pairs: {expected_pairs}")
    else:
        print("\n⚠️  No basename duplicates found!")
        print("   This means no images share the same filename across folders.")
        print("   Expected: 200000.jpg in both original/ and attack/ folders")
    
    print("\n" + "=" * 60)
    print("RECOMMENDATION")
    print("=" * 60)
    
    if has_original and len(duplicates_by_name) > 0:
        print("✅ Dataset structure looks GOOD!")
        print(f"   Should generate ~{expected_pairs} ground truth pairs")
    else:
        print("⚠️  Dataset structure needs adjustment:")
        if not has_original:
            print("   1. Create an 'original' folder")
            print("   2. Move original images there")
        if len(duplicates_by_name) == 0:
            print("   3. Ensure attack images have same basenames as originals")
            print("      Example: original/img001.jpg → attacks/blur/img001.jpg")

if __name__ == "__main__":
    analyze_dataset(DATASET_PATH)