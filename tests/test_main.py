from __future__ import annotations

import json
from pathlib import Path

from fakeshot.main import generate_dummy_shots
from fakeshot.template import Template


def test_default_template_structure(tmp_path: Path):
    """Test that default template generates expected directory structure."""

    template = Template()

    generate_dummy_shots(template, str(tmp_path))

    # Default template should create:
    # prj/001/0010/comp/v001/, prj/001/0010/anim/v001/
    expected_paths = [
        'prj/001/0010/comp/v001',
        'prj/001/0010/anim/v001',
        'prj/001/0020/comp/v001',
        'prj/001/0020/anim/v001',
        'prj/002/0010/comp/v001',
        'prj/002/0010/anim/v001',
        'prj/002/0020/comp/v001',
        'prj/002/0020/anim/v001',
    ]

    assert all((tmp_path / f).exists() for f in expected_paths)


def test_frame_range_generation(tmp_path: Path):
    """Test that correct number of frames are generated."""

    template = Template()

    generate_dummy_shots(template, str(tmp_path))

    # Check one specific directory for frame count
    test_dir = tmp_path / 'prj/001/0010/comp/v001'
    exr_files = list(test_dir.glob('*.exr'))

    # Default template: frames 1001-1009 (end_frame is exclusive)
    expected_frame_count = template.end_frame - template.start_frame
    assert len(exr_files) == expected_frame_count

    # Check frame numbering
    frame_numbers = [
        int(exr_file.stem.split('.')[-1])
        for exr_file in exr_files
    ]

    frame_numbers.sort()
    expected_frames = list(range(template.start_frame, template.end_frame))
    assert frame_numbers == expected_frames


def test_exr_files_are_valid(tmp_path: Path):
    """Test that generated EXR files are actually valid."""

    template = Template()
    # Use smaller template for faster testing
    template.scene = '001'
    template.shot = '0010'
    template.task = 'comp'
    template.start_frame = 1001
    template.end_frame = 1003  # Only 2 frames

    generate_dummy_shots(template, str(tmp_path))

    # Find an EXR file
    exr_files = list(tmp_path.rglob('*.exr'))
    assert exr_files, 'No EXR files generated'

    # Try to verify it's a valid EXR (simple check)
    test_file = exr_files[0]
    assert test_file.stat().st_size > 0, 'EXR file is empty'

    # Check file has expected dimensions in header (basic validation)
    with open(test_file, 'rb') as f:
        header = f.read(100)  # Read first 100 bytes
        assert b'OpenEXR' in header or header.startswith(b'\x76\x2f\x31\x01'), \
            "File doesn't appear to be a valid EXR"


def test_custom_template_via_json(tmp_path: Path):
    """Test using a custom template loaded from JSON."""

    custom_template_data: dict[str, str | int] = {
        'show': 'foo',
        'scene': 'sc01',
        'shot': 'sh010',
        'task': 'lighting',
        'version': 'v002',
        'start_frame': 1050,
        'end_frame': 1052,
        'width': 1920,
        'height': 1080,
        'path_pattern': '{show}/test/{shot}/{task}_{version}',
        'file_pattern': '{shot}.{frame}',
    }

    # Create template file
    template_file = tmp_path / 'custom_template.json'
    with open(template_file, 'w') as f:
        json.dump(custom_template_data, f)

    # Load and use template
    template = Template()
    with open(template_file) as f:
        template.update(json.load(f))

    output_dir = tmp_path / 'output'
    generate_dummy_shots(template, str(output_dir))

    # Check custom structure was created
    expected_path = output_dir / 'foo/test/sh010/lighting_v002'
    assert expected_path.exists(), f"Custom template structure not created: {expected_path}"

    expected_filename = expected_path / 'sh010.1050.exr'
    assert expected_filename.exists(), f"Custom template structure not created: {expected_path}"

    # Check custom frame range
    exr_files = list(expected_path.glob('*.exr'))
    assert len(exr_files) == 2, f"Expected 2 frames, got {len(exr_files)}"


if __name__ == '__main__':
    print('Running simple smoke test...')

    # Test template creation
    template = Template()
    print(f"Default template created: show={template.show}, scene={template.scene}")

    # Test shot generation
    shots = list(template.generate_shots())
    print(f"Generated {len(shots)} shots")

    if shots:
        print(f"First shot: {shots[0]}")

    print('Test passed!')
