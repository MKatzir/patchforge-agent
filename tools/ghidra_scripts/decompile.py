# Ghidra Jython Script - Decompilation Analysis
# This script runs inside Ghidra's headless analyzer
# It exports decompiled pseudocode in JSON format using the Ghidra decompiler

import json
from ghidra.app.decompiler import DecompileOptions, DecompInterface

def decompile_function(function, decompiler):
    """Decompile a single function"""
    try:
        decompiler.openProgram(currentProgram)
        
        options = DecompileOptions()
        decompiler.setOptions(options)
        
        results = decompiler.decompileFunction(function, 30, None)
        
        if results.decompileCompleted():
            pseudocode = results.getDecompiledFunction().getC()
            
            return {
                'name': function.getName(),
                'address': str(function.getEntryPoint()),
                'size': function.getBody().getNumAddresses(),
                'pseudocode': pseudocode,
                'status': 'success'
            }
        else:
            return {
                'name': function.getName(),
                'address': str(function.getEntryPoint()),
                'status': 'failed',
                'error': 'Decompilation did not complete'
            }
    except Exception as e:
        return {
            'name': function.getName(),
            'address': str(function.getEntryPoint()),
            'status': 'error',
            'error': str(e)
        }

def should_process_function(function, filter_dict):
    """Check if function matches the given filter"""
    if not filter_dict:
        return True
    
    name = function.getName()
    addr = str(function.getEntryPoint())

    if filter_dict.get('names') and name in filter_dict['names']:
        return True
    if filter_dict.get('address') and address_matches(addr, filter_dict['address']):
        return True
    
    return False

def address_matches(addr_a, addr_b):
    """Compare two addresses, handling different formats"""
    try:
        a = int(str(addr_a), 16) if isinstance(addr_a, basestring) else int(addr_a)
        b = int(str(addr_b), 16) if isinstance(addr_b, basestring) else int(addr_b)
        return a == b
    except:
        return str(addr_a) == str(addr_b)

def parse_filter_args():
    """Parse script arguments into a filter dict"""
    try:
        args = getScriptArgs()
    except:
        return None

    filter_dict = {}
    i = 0
    while i < len(args):
        if args[i] == '--names' and i + 1 < len(args):
            filter_dict['names'] = set(args[i + 1].split(','))
            i += 2
        elif args[i] == '--address' and i + 1 < len(args):
            filter_dict['address'] = args[i + 1]
            i += 2
        else:
            i += 1

    return filter_dict if filter_dict else None

def extract_decompiled_functions(filter_dict):
    """Extract decompiled pseudocode for functions, optionally filtered"""
    functions = []
    decompiler = DecompInterface()
    
    try:
        function_manager = currentProgram.getFunctionManager()
        
        for function in function_manager.getFunctions(True):
            if not should_process_function(function, filter_dict):
                continue

            try:
                func_decompiled = decompile_function(function, decompiler)
                functions.append(func_decompiled)
            except Exception as e:
                functions.append({
                    'name': function.getName(),
                    'address': str(function.getEntryPoint()),
                    'status': 'error',
                    'error': str(e)
                })
    
    finally:
        decompiler.closeProgram()
    
    return functions

def main():
    """Main script entry point"""
    try:
        filter_dict = parse_filter_args()
        output = {
            'program_name': currentProgram.getName(),
            'image_base': str(currentProgram.getImageBase()),
            'entry_point': str(currentProgram.getMinAddress()),
            'architecture': currentProgram.getLanguage().getLanguageID(),
            'functions': extract_decompiled_functions(filter_dict)
        }
        
        print(json.dumps(output, indent=2))
    except Exception as e:
        error_output = {
            'error': str(e),
            'timestamp': str(java.lang.System.currentTimeMillis())
        }
        print(json.dumps(error_output, indent=2))

if __name__ == '__main__':
    main()
