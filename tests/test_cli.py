from pathlib import Path

from logiclens.cli import main


FIXTURE = Path(__file__).parent / "fixtures" / "tiny_python"


def test_map_then_list_files(tmp_path: Path, capsys) -> None:
    database = tmp_path / "tiny.sqlite"

    assert main(["map", str(FIXTURE), "--db", str(database)]) == 0
    map_output = capsys.readouterr().out
    assert "Mapped 6 files" in map_output

    assert main(["files", "--db", str(database)]) == 0
    files_output = capsys.readouterr().out
    assert "README.md\tdocumentation\tmarkdown" in files_output
    assert "src/shop/main.py\tsource\tpython" in files_output
