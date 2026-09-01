import json
import subprocess
from pathlib import Path


def test_i18n_tr_en_recursive_key_parity():
    """
    CRITICAL INVARIANT 24:
    Proves 100% key parity between TR and EN locale dictionaries.
    Missing in TR == 0 and Missing in EN == 0.
    """
    node_script = """
    import('./frontend/src/locales/tr.ts').then(trMod => {
      import('./frontend/src/locales/en.ts').then(enMod => {
        const tr = trMod.tr || trMod.default;
        const en = enMod.en || enMod.default;
        
        function flattenKeys(obj, prefix = '') {
          let keys = [];
          for (let k of Object.keys(obj)) {
            const full = prefix ? prefix + '.' + k : k;
            if (typeof obj[k] === 'object' && obj[k] !== null && !Array.isArray(obj[k])) {
              keys.push(...flattenKeys(obj[k], full));
            } else {
              keys.push(full);
            }
          }
          return keys;
        }
        
        const trKeys = new Set(flattenKeys(tr));
        const enKeys = new Set(flattenKeys(en));
        
        const missingInEn = [...trKeys].filter(k => !enKeys.has(k));
        const missingInTr = [...enKeys].filter(k => !trKeys.has(k));
        
        console.log(JSON.stringify({
          trCount: trKeys.size,
          enCount: enKeys.size,
          missingInEn,
          missingInTr
        }));
      });
    });
    """
    proc = subprocess.run(["node", "-e", node_script], capture_output=True, text=True, cwd=str(Path(__file__).parents[3]))
    assert proc.returncode == 0, f"Node i18n script failed: {proc.stderr}"
    
    result = json.loads(proc.stdout.strip())
    assert result["trCount"] > 0
    assert result["enCount"] > 0
    assert result["trCount"] == result["enCount"]
    assert len(result["missingInEn"]) == 0, f"Keys missing in EN: {result['missingInEn']}"
    assert len(result["missingInTr"]) == 0, f"Keys missing in TR: {result['missingInTr']}"
