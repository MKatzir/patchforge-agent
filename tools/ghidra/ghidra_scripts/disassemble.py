import json
import os

def extract_disassembly(function):
    instructions = []
    try:
        listing = currentProgram.getListing()
        body = function.getBody()
        for instruction in listing.getInstructions(body, True):
            instr_dict = {
                'address': str(instruction.getAddress()),
                'mnemonic': str(instruction.getMnemonicString()),
                'operands': str(instruction.getDefaultOperandRepresentation()),
                'bytes': ''.join(format(b & 0xff, '02x') for b in instruction.getBytes()),
                'length': instruction.getLength(),
                'flow_type': str(instruction.getFlowType())
            }
            instructions.append(instr_dict)
    except Exception as e:
        print("Error extracting instruction: " + str(e))
    return instructions

def address_matches(addr_a, addr_b):
    try:
        a = int(str(addr_a), 16) if isinstance(addr_a, basestring) else int(addr_a)
        b = int(str(addr_b), 16) if isinstance(addr_b, basestring) else int(addr_b)
        
        # SMART OFFSET FIX
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

def should_process_function(function, filter_dict):
    if not filter_dict: return True
    if filter_dict.get('names') and str(function.getName()) in filter_dict['names']: return True
    if filter_dict.get('address') and address_matches(str(function.getEntryPoint()), filter_dict['address']): return True
    return False

def extract_functions_info(filter_dict):
    functions = []
    try:
        function_manager = currentProgram.getFunctionManager()
        for function in function_manager.getFunctions(True):
            if not should_process_function(function, filter_dict): continue
            try:
                func_dict = {
                    'name': str(function.getName()),
                    'address': str(function.getEntryPoint()),
                    'size': function.getBody().getNumAddresses(),
                    'called_functions': [],
                    'disassembly': extract_disassembly(function)
                }
                reference_manager = currentProgram.getReferenceManager()
                for ref in reference_manager.getReferencesFrom(function.getEntryPoint()):
                    if ref.getReferenceType().isCall():
                        func_dict['called_functions'].append({
                            'address': str(ref.getToAddress()),
                            'type': str(ref.getReferenceType())
                        })
                functions.append(func_dict)
            except Exception as e:
                print("Error processing function: " + str(e))
    except Exception as e:
        print("Error extracting functions: " + str(e))
    return functions

def main():
    try:
        filter_dict = parse_filter_args()
        output = {
            'program_name': str(currentProgram.getName()),
            'image_base': str(currentProgram.getImageBase()),
            'entry_point': str(currentProgram.getMinAddress()),
            'architecture': str(currentProgram.getLanguage().getLanguageID()),
            'functions': extract_functions_info(filter_dict)
        }
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
