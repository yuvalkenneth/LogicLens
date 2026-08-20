from pathlib import Path
import json

from logiclens.cli import main


FIXTURE = Path(__file__).parent / "fixtures" / "tiny_python"


def test_map_then_list_files(tmp_path: Path, capsys) -> None:
    database = tmp_path / "tiny.sqlite"

    assert main(["map", str(FIXTURE), "--db", str(database)]) == 0
    map_output = capsys.readouterr().out
    assert "Mapped 6 files" in map_output
    assert "Python modules: 4; imports: 3" in map_output

    assert main(["files", "--db", str(database)]) == 0
    files_output = capsys.readouterr().out
    assert "README.md\tdocumentation\tmarkdown" in files_output
    assert "src/shop/main.py\tsource\tpython" in files_output

    assert main(["modules", "--db", str(database)]) == 0
    modules_output = capsys.readouterr().out
    assert "shop\tpackage\tsrc/shop/__init__.py" in modules_output
    assert "shop.main\t.repository\tshop.repository\tsrc/shop/main.py:1:1" in modules_output

    assert (
        main(
            [
                "context",
                "repository-brief",
                "--db",
                str(database),
                "--json",
            ]
        )
        == 0
    )
    context = json.loads(capsys.readouterr().out)
    assert context["documents"][0]["content"].startswith("# Tiny Shop")
    assert context["imports"][0]["target"] == "shop.repository"
