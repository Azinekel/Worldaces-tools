#!/usr/bin/env python3
"""Generate docs/index.html by listing all tools in tools/*.

Reads tools/<x>/metadata.json when it exists (otherwise it just uses the folder name) and produces a
simple static page. Called by the `.github/workflows/pages.yml` workflow on each push to main.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = ROOT / "tools"
DOCS_DIR = ROOT / "docs"
DOCS_PY = DOCS_DIR / "py"

INDEX_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>WorldAces Community Tools</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
    body {{ font-family: system-ui, sans-serif; max-width: 780px; margin: 3rem auto; padding: 0 1rem; color: #1a1f26; }}
    h1 {{ margin-bottom: 0.2rem; }}
    .sub {{ color: #5a6472; margin-top: 0; }}
    .card {{ border: 1px solid #e2e6eb; border-radius: 10px; padding: 1rem 1.2rem; margin: 1rem 0; }}
    .card h2 {{ margin: 0 0 0.3rem 0; font-size: 1.1rem; }}
    .tags span {{ display: inline-block; background: #eef1f5; border-radius: 999px; padding: 0.15rem 0.6rem; font-size: 0.78rem; margin-right: 0.3rem; color: #444; }}
    a {{ color: #2a67c9; }}
</style>
</head>
<body>
<h1>WorldAces Community Tools</h1>
<p class="sub">Tools shared by the community. Click a tool for instructions.</p>
{cards}
</body>
</html>
"""

CARD_TEMPLATE = """<div class="card">
    <h2><a href="{tool_page}">{name}</a></h2>
    <p>{description}</p>
    <div class="tags">{tags}</div>
    <p><small>by {author}</small></p>
</div>
"""

PER_TOOL_HTML = """<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>__TITLE__ — Browser</title>
    <style>
        body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;margin:18px}}
        textarea{{width:100%;height:280px;font-family:monospace}}
        .row{{display:flex;gap:12px;align-items:center;margin-top:8px}}
        .col{{flex:1}}
        canvas,img{{max-width:100%;border:1px solid #ddd}}
    </style>
</head>
<body>
    <h1>__TITLE__ - browser version</h1>
    <p>Paste a JSON array (list of objects) or load a file, then click <em>Generate</em>.</p>

    <div class="row">
        <div class="col">
            <label for="file">Load a JSON/CSV file: </label>
            <input id="file" type="file" accept=".json,.csv" />
        </div>
        <div>
            <button id="loadExample">Load example</button>
        </div>
    </div>

    <textarea id="input" placeholder='[ { "amount": 100, "source": "Salary" }, ... ]'></textarea>

    <div class="row">
        <label>Theme: <select id="theme"><option>light</option><option>dark</option></select></label>
        <button id="gen">Generate</button>
    </div>

    <h2>Result</h2>
    <div id="output">No rendering yet</div>

    <script type="module">
        const indexURL = 'https://cdn.jsdelivr.net/pyodide/v0.23.3/full/';
        let pyodide = null;
        let render_fn = null;

        document.getElementById('file').addEventListener('change', async (ev)=>{
            const f = ev.target.files[0];
            if(!f) return;
            const txt = await f.text();
            if(f.name.toLowerCase().endsWith('.csv')){
                const lines = txt.split(/\r?\n/).filter(Boolean);
                const headers = lines.shift().split(/,|;|\t/).map(h=>h.trim());
                const arr = lines.map(l=>{
                    const cols = l.split(/,|;|\t/);
                    const obj = {};
                    headers.forEach((h,i)=>obj[h]=cols[i]===undefined?"":cols[i]);
                    return obj;
                });
                document.getElementById('input').value = JSON.stringify(arr, null, 2);
            } else {
                document.getElementById('input').value = txt;
            }
        });

            document.getElementById('loadExample').addEventListener('click', ()=>{
            fetch('__EXAMPLE_PATH__').then(r=>r.text()).then(t=>document.getElementById('input').value=t).catch(()=>{
                document.getElementById('input').value = JSON.stringify([
                    {"amount": 1000, "source": "Salary"},
                    {"amount": -120, "source": "Groceries"},
                    {"amount": -60, "source": "Transport"},
                    {"amount": 200, "source": "Freelance"}
                ], null, 2);
            })
        });

        async function ensurePyodide(){
            if(pyodide) return;
            const load = document.createElement('div');
            load.id='loading';
            load.textContent = 'Loading Pyodide and matplotlib... (first load ~30-40 MB)';
            document.body.prepend(load);
            pyodide = await loadPyodide({indexURL});
            await pyodide.loadPackage(['micropip']);
            await pyodide.loadPackage(['matplotlib']);
            const pyCode = await (await fetch('__PY_PATH__')).text();
            pyodide.runPython(pyCode);
            render_fn = pyodide.globals.get('render_from_json');
            load.remove();
        }

        document.getElementById('gen').addEventListener('click', async ()=>{
            try{
                await ensurePyodide();
                const txt = document.getElementById('input').value.trim();
                if(!txt){ alert('Enter JSON or load a file'); return; }
                const theme = document.getElementById('theme').value;
                const pyres = render_fn(txt, theme, null, null, "", 150);
                const b64 = pyres.toString();
                document.getElementById('output').innerHTML = `<img alt="result" src="data:image/png;base64,${b64}" />`;
                pyres.destroy && pyres.destroy();
            }catch(e){
                console.error(e);
                alert('Error: '+e);
            }
        });

        (function(){
            const s = document.createElement('script');
            s.src = 'https://cdn.jsdelivr.net/pyodide/v0.23.3/full/pyodide.js';
            s.onload = ()=>console.log('pyodide script loaded');
            document.head.appendChild(s);
        })();
    </script>
</body>
</html>
"""


def main():
        repo = "Worldaces-community/Worldaces-tools"
        cards = []
        DOCS_DIR.mkdir(exist_ok=True)
        DOCS_PY.mkdir(exist_ok=True)

        for tool_dir in sorted(TOOLS_DIR.iterdir()):
                if not tool_dir.is_dir():
                        continue
                meta_path = tool_dir / "metadata.json"
                if meta_path.exists():
                        meta = json.loads(meta_path.read_text())
                else:
                        meta = {"name": tool_dir.name, "description": "", "author": "?", "tags": []}

                slug = tool_dir.name
                tags = "".join(f"<span>{t}</span>" for t in meta.get("tags", []))

                # Create tool page if runnable_in_browser
                tool_page = f"https://github.com/{repo}/tree/main/tools/{slug}"
                if meta.get("runnable_in_browser"):
                        py_src = tool_dir / meta.get("browser_entry", "browser.py")
                        if py_src.exists():
                                py_dest = DOCS_PY / f"{slug}_browser.py"
                                shutil.copy(py_src, py_dest)
                                py_path = f"py/{slug}_browser.py"
                        else:
                                py_path = ""

                        # copy example if present
                        example_src_candidates = [tool_dir / 'example_input.json', tool_dir / 'example.json']
                        example_path = ''
                        for c in example_src_candidates:
                                if c.exists():
                                        dst = DOCS_DIR / f"{slug}_example.json"
                                        shutil.copy(c, dst)
                                        example_path = f"{slug}_example.json"
                                        break

                        # Prefer a per-tool HTML page if provided in the tool folder (tools/<slug>/browser.html).
                        tool_html_src = tool_dir / 'browser.html'
                        if tool_html_src.exists():
                            raw = tool_html_src.read_text()
                            out = raw.replace('__TITLE__', meta.get('name', slug))
                            out = out.replace('__PY_PATH__', py_path if py_path else '')
                            out = out.replace('__EXAMPLE_PATH__', example_path or '#')
                            page_file = DOCS_DIR / f"{slug}.html"
                            page_file.write_text(out)
                            tool_page = f"{slug}.html"
                        elif not py_path:
                            tool_page = f"https://github.com/{repo}/tree/main/tools/{slug}"
                        else:
                            page_file = DOCS_DIR / f"{slug}.html"
                            page_file.write_text(PER_TOOL_HTML.replace('__TITLE__', meta.get('name', slug))
                                                    .replace('__PY_PATH__', py_path)
                                                    .replace('__EXAMPLE_PATH__', example_path or '#'))
                            tool_page = f"{slug}.html"

                cards.append(CARD_TEMPLATE.format(
                        tool_page=tool_page, name=meta.get("name", slug), description=meta.get("description", ""),
                        tags=tags, author=meta.get("author", "?"),
                ))

        (DOCS_DIR / "index.html").write_text(INDEX_TEMPLATE.format(cards="\n".join(cards)))
        print(f"wrote docs/index.html with {len(cards)} tool(s)")


if __name__ == "__main__":
        main()
