// Export every function of the current program, one per line: entry, body size, reference count to the entry, name.
// usage (headless): -postScript ExportFuncs.java OUT.tsv
//@category MHF
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceManager;
import java.io.FileWriter;
import java.io.PrintWriter;

public class ExportFuncs extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] a = getScriptArgs();
        ReferenceManager rm = currentProgram.getReferenceManager();
        int n = 0;
        try (PrintWriter w = new PrintWriter(new FileWriter(a[0]))) {
            for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
                int refs = 0;
                for (Reference r : rm.getReferencesTo(f.getEntryPoint())) refs++;
                w.printf("%s\t%d\t%d\t%s%n", f.getEntryPoint(), f.getBody().getNumAddresses(), refs, f.getName());
                n++;
            }
        }
        println("ExportFuncs: " + n + " functions -> " + a[0]);
    }
}
