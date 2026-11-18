from __future__ import annotations

import io
import csv
import sys
import json
from pathlib import Path

import pytest
from _pytest.monkeypatch import MonkeyPatch

from fakeshot.template import Template
from fakeshot.__main__ import main
from fakeshot.generate_csv import generate_csv
from fakeshot.generate_shots import generate_shots


def test_default_template_structure(tmp_path: Path):
    """Test that default template generates expected directory structure."""

    template = Template()
    template.show = 'prj'
    template.scene = '001,002'
    template.shot = '0010,0020'
    template.task = 'comp,anim'
    generate_shots(template, str(tmp_path))

    # Default template should create:
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


def test_flat_directory_generation(tmp_path: Path):
    """Test that flat mode generates files directly in the output directory."""

    template = Template()
    template.show = 'prj'
    template.scene = '001'
    template.shot = '0010'
    template.task = 'comp'
    template.start_frame = 1001
    template.end_frame = 1003

    generate_shots(template, str(tmp_path), is_flat=True)

    expected_files = [
        'prj_001_0010_comp_v001.1001.exr',
        'prj_001_0010_comp_v001.1002.exr',
    ]

    assert all((tmp_path / f).exists() for f in expected_files)
    assert not (tmp_path / 'prj').exists()


def test_frame_range_generation(tmp_path: Path):
    """Test that correct number of frames are generated."""

    template = Template()

    generate_shots(template, str(tmp_path))

    # Check one specific directory for frame count
    test_dir = tmp_path / 'prj/001/0010/comp/v001'
    exr_files = list(test_dir.glob('*.exr'))

    # Default template: frames 1001-1010 (end_frame is inclusive)
    expected_frame_count = template.end_frame - template.start_frame + 1
    assert len(exr_files) == expected_frame_count

    # Check frame numbering
    frame_numbers = [
        int(exr_file.stem.split('.')[-1])
        for exr_file in exr_files
    ]

    frame_numbers.sort()
    expected_frames = list(range(template.start_frame, template.end_frame + 1))
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

    generate_shots(template, str(tmp_path))

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
        'end_frame': 1051,
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
    generate_shots(template, str(output_dir))

    # Check custom structure was created
    expected_path = output_dir / 'foo/test/sh010/lighting_v002'
    assert expected_path.exists(), f"Custom template structure not created: {expected_path}"

    expected_filename = expected_path / 'sh010.1050.exr'
    assert expected_filename.exists(), f"Custom template structure not created: {expected_path}"

    # Check custom frame range
    exr_files = list(expected_path.glob('*.exr'))
    assert len(exr_files) == 2, f"Expected 2 frames, got {len(exr_files)}"


def test_generate_csv_to_stringio(monkeypatch: MonkeyPatch):
    """Test generate_csv outputs correct CSV to stdout when no output path is given."""

    template = Template()
    captured = io.StringIO()
    monkeypatch.setattr(sys, 'stdout', captured)
    generate_csv(template)
    output = captured.getvalue()
    assert 'scene,shot,task' in output
    # Check that at least one expected row is present
    assert '001,0010,comp' in output or '001,0010,anim' in output


def test_generate_csv_to_file(tmp_path: Path):
    """Test generate_csv writes correct CSV file when output path is given."""

    template = Template()
    generate_csv(template, str(tmp_path))
    csv_file = tmp_path / 'shots.csv'
    assert csv_file.exists()
    with open(csv_file, newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert rows, 'CSV file should not be empty'
        # Check that all required columns exist
        assert set(rows[0].keys()) == {'scene', 'shot', 'task'}
        # Check that at least one row matches expected template data
        assert any(row['scene'] == '001' and row['shot'] == '0010' for row in rows)


def test_generate_csv_custom_template(tmp_path: Path):
    """Test generate_csv with a custom template produces expected CSV rows."""

    template = Template()
    template.scene = 'A,B'
    template.shot = '10'
    template.task = 'lighting,comp'

    generate_csv(template, str(tmp_path))
    csv_file = tmp_path / 'shots.csv'
    with open(csv_file, newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        expected = [
            {'scene': 'A', 'shot': '10', 'task': 'lighting'},
            {'scene': 'A', 'shot': '10', 'task': 'comp'},
            {'scene': 'B', 'shot': '10', 'task': 'lighting'},
            {'scene': 'B', 'shot': '10', 'task': 'comp'},
        ]
        assert all(row in rows for row in expected)
        assert len(rows) == 4



def run_cli(monkeypatch: MonkeyPatch, *argv: str) -> None:
    monkeypatch.setattr(sys, 'argv', ['fakeshot', *argv])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0


def test_cli_flag_beats_template_file(tmp_path: Path, monkeypatch: MonkeyPatch):
    """Flags typed by the user override the template file; the file overrides defaults."""

    template_file = tmp_path / 'template.json'
    template_file.write_text(json.dumps({
        'show': 'from_file', 'scene': ['001'], 'shot': '0010', 'task': 'comp',
        'start_frame': '1001', 'end_frame': 1001,
    }))

    out = tmp_path / 'out'
    run_cli(monkeypatch, '--template', str(template_file), '--show', 'from_cli', '--out', str(out))

    files = [p.name for p in out.rglob('*.exr')]
    assert files == ['from_cli_001_0010_comp_v001.1001.exr']


def test_cli_csv_creates_missing_out_dir(tmp_path: Path, monkeypatch: MonkeyPatch):
    out = tmp_path / 'missing' / 'dir'
    run_cli(monkeypatch, '--csv', '--out', str(out))
    assert (out / 'shots.csv').exists()


def test_template_update_rejects_bad_data():
    with pytest.raises(ValueError, match='start-frame'):
        Template().update({'start-frame': 1001})

    with pytest.raises(ValueError):
        Template().update({'start_frame': 'abc'})


def test_start_after_end_frame_raises(tmp_path: Path):
    template = Template(start_frame=1010, end_frame=1001)
    with pytest.raises(ValueError, match='start_frame'):
        generate_shots(template, str(tmp_path))


def test_flat_does_not_mutate_template(tmp_path: Path):
    template = Template(scene='001', shot='0010', task='comp', end_frame=1001)
    generate_shots(template, str(tmp_path), is_flat=True)
    assert template.path_pattern == Template().path_pattern
