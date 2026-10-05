import os
import nbformat as nbf

import os
import json
import nbformat as nbf

def assemble_notebook(content: str, dataset_ref: str, user_id: str) -> str:
    nb = nbf.v4.new_notebook()
    
    # Kernel metadata so Papermill executes it automatically
    nb.metadata = {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "name": "python",
            "version": "3"
        }
    }
    
    # Parse the LLM output into Markdown and Code cells
    # We split by '```' to separate markdown from code blocks
    blocks = content.split('```')
    for block in blocks:
        if block.startswith('python'):
            # This is a code block
            code = block[6:].strip() # Strip the 'python' string and whitespace
            if code:
                nb.cells.append(nbf.v4.new_code_cell(code))
        else:
            # This is a markdown block
            md = block.strip()
            if md:
                nb.cells.append(nbf.v4.new_markdown_cell(md))
    
    workspace = f"./workspace_{user_id}"
    os.makedirs(workspace, exist_ok=True)
    notebook_path = os.path.join(workspace, "automated_eda.ipynb")
    
    with open(notebook_path, "w", encoding="utf-8") as f:
        nbf.write(nb, f)
        
    return notebook_path