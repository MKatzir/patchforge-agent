import os
import sys
from java.io import File

try:
    # Attempt to import the official BinExport plugin classes
    from com.google.security.binexport import BinExportExporter
except ImportError:
    print("ERROR: BinExport plugin not found in Ghidra 11.0.3.")
    sys.exit(1)

def main():
    try:
        output_dir = os.environ.get('GHIDRA_OUTPUT_DIR', '/work/output')
        file_name = currentProgram.getName() + ".BinExport"
        output_file = File(output_dir, file_name)
        
        # Initialize and run the exporter
        exporter = BinExportExporter()
        
        # Export the program
        success = exporter.export(output_file, currentProgram, currentProgram.getAddressFactory().getAddressSet(), monitor)
        
        if success:
            print("Successfully exported: " + output_file.getAbsolutePath())
        else:
            print("ERROR: Failed to export " + file_name)
            
    except Exception as e:
        print("ERROR during BinExport: " + str(e))

if __name__ == '__main__':
    main()
