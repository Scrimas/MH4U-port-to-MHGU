// Decompile the functions containing the given addresses into OUT (C text, in argument order), each headed by
// its entry, size and callers. An address outside every function gets a new function there (not saved).
// usage (headless, on the analysed project): -process mhfo-hd.dll -noanalysis -readOnly
//        -postScript Decomp.java OUT.c ADDR...        (ADDR in hex, 0x optional)
//@category MHF
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.Set;
import java.util.TreeSet;

public class Decomp extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] a = getScriptArgs();
        DecompInterface ifc = new DecompInterface();
        ifc.openProgram(currentProgram);
        FunctionManager fm = currentProgram.getFunctionManager();
        try (PrintWriter w = new PrintWriter(new FileWriter(a[0]))) {
            for (int i = 1; i < a.length; i++) {
                Address ad = toAddr(a[i].replaceFirst("^0x", ""));
                Function f = fm.getFunctionContaining(ad);
                // only reached through a data table (e.g. a callback list): analysis made no function; make one
                // here (in memory: the project is opened read-only)
                if (f == null && getInstructionAt(ad) == null) disassemble(ad);
                if (f == null) f = createFunction(ad, null);
                if (f == null) {
                    w.printf("// ==== %s: no function%n%n", a[i]);
                    continue;
                }
                Set<String> callers = new TreeSet<>();
                for (Function c : f.getCallingFunctions(monitor)) callers.add(c.getEntryPoint().toString());
                w.printf("// ==== %s  entry %s  size %d  callers %s%n", a[i], f.getEntryPoint(),
                         f.getBody().getNumAddresses(), callers);
                DecompileResults r = ifc.decompileFunction(f, 180, monitor);
                if (r.decompileCompleted()) w.println(r.getDecompiledFunction().getC());
                else w.printf("// decompile failed: %s%n%n", r.getErrorMessage());
            }
        }
        ifc.dispose();
    }
}
