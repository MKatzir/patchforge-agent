# Ghidra Jython Script - Disassembly Analysis
# This script runs inside Ghidra's headless analyzer
# It exports disassembly in JSON format

import json

def extract_disassembly(function):
    """Extract disassembly for a function"""
    instructions = []
    
    try:
        listing = currentProgram.getListing()
        body = function.getBody()
        
        for instruction in listing.getInstructions(body, True):
            instr_dict = {
                'address': str(instruction.getAddress()),
                'mnemonic': instruction.getMnemonicString(),
                'operands': instruction.getOperandRepresentationList(),
                'bytes': ''.join(format(b & 0xff, '02x') for b in instruction.getBytes()),
                'length': instruction.getLength(),
                'flow_type': str(instruction.getFlowType())
            }
            instructions.append(instr_dict)
    except Exception as e:
        print("Error extracting instruction: " + str(e))
    
    return instructions

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

def extract_functions_info(filter_dict):
    """Extract information about functions, optionally filtered"""
    functions = []
    
    try:
        function_manager = currentProgram.getFunctionManager()
        
        for function in function_manager.getFunctions(True):
            if not should_process_function(function, filter_dict):
                continue

            try:
                func_dict = {
                    'name': function.getName(),
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
    """Main script entry point"""
    try:
        filter_dict = parse_filter_args()
        output = {
            'program_name': currentProgram.getName(),
            'image_base': str(currentProgram.getImageBase()),
            'entry_point': str(currentProgram.getMinAddress()),
            'architecture': currentProgram.getLanguage().getLanguageID(),
            'functions': extract_functions_info(filter_dict)
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
