import json
import os
from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

def address_matches(addr_a, addr_b):
    try:
        a = int(str(addr_a), 16) if isinstance(addr_a, basestring) else int(addr_a)
        b = int(str(addr_b), 16) if isinstance(addr_b, basestring) else int(addr_b)
        
        # SMART OFFSET FIX: Automatically add Image Base if 'b' is just a raw offset
        image_base = currentProgram.getImageBase().getOffset()
        if b > 0 and b < image_base:
            b += image_base
            
        return a == b
    except:
        return str(addr_a) == str(addr_b)

def parse_filter_args():
    filter_dict = {}
    names = os.environ.get('GHIDRA_FUNCTION_NAMES')
    if names: filter_dict['names'] = set(names.split(','))
    addr = os.environ.get('GHIDRA_FUNCTION_ADDRESS')
    if addr: filter_dict['address'] = addr
    return filter_dict if filter_dict else None

def should_process(function, filter_dict):
    if not filter_dict: return True
    if filter_dict.get('names') and str(function.getName()) in filter_dict['names']: return True
    if filter_dict.get('address') and address_matches(str(function.getEntryPoint()), filter_dict['address']): return True
    return False

def decompile_functions(filter_dict):
    ifc = DecompInterface()
    ifc.openProgram(currentProgram)
    monitor = ConsoleTaskMonitor()
    
    results = []
    fm = currentProgram.getFunctionManager()
    
    for function in fm.getFunctions(True):
        if not should_process(function, filter_dict): continue
            
        try:
            res = ifc.decompileFunction(function, 60, monitor)
            c_code = res.getDecompiledFunction().getC() if res.decompileCompleted() else "Decompilation failed or timed out"
            results.append({
                "name": str(function.getName()),
                "address": str(function.getEntryPoint()),
                "c_code": str(c_code)
            })
        except Exception as e:
            results.append({"name": str(function.getName()), "address": str(function.getEntryPoint()), "error": str(e)})
    return results

def main():
    try:
        filter_dict = parse_filter_args()
        funcs = decompile_functions(filter_dict)
        output = {"program_name": str(currentProgram.getName()), "functions": funcs}
        
        out_path = os.environ.get('GHIDRA_OUTPUT_FILE')
        if out_path:
            with open(out_path, 'w') as f: f.write(json.dumps(output, indent=2))
        else:
            print(json.dumps(output, indent=2))
    except Exception as e:
        import java.lang.System
        error_output = {"error": str(e), "timestamp": str(java.lang.System.currentTimeMillis())}
        out_path = os.environ.get('GHIDRA_OUTPUT_FILE')
        if out_path:
            with open(out_path, 'w') as f: f.write(json.dumps(error_output, indent=2))
        else:
            print(json.dumps(error_output, indent=2))

if __name__ == '__main__':
    main()
