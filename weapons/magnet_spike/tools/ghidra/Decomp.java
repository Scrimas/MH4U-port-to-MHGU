// Decompile the functions containing the given addresses into OUT (C text, in argument order), each headed by
// its entry, size and callers. An address outside every function gets a new function there (not saved).
// usage (headless, on the analysed project): -process mhfo-hd.dll -noanalysis -readOnly
//        -postScript Decomp.java OUT.c ADDR...        (ADDR in hex, 0x optional)
// env DECOMP_RETURNING = comma-separated callee entries that analysis wrongly made no-return (GU's memset thunk
// 0x13efd44 / 0x13efd7c): cleared in memory, and the requested functions' bodies regrown past their calls.
//@category MHF
import ghidra.app.cmd.function.CreateFunctionCmd;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.HashSet;
import java.util.Set;
import java.util.TreeSet;

public class Decomp extends GhidraScript {
    private final Set<Address> returning = new HashSet<>();

    /** calls to a `returning` callee get their fall-through back and the body is recomputed; true when it grew */
    private boolean regrow(Function f) throws Exception {
        long before = f.getBody().getNumAddresses();
        InstructionIterator it = currentProgram.getListing().getInstructions(f.getBody(), true);
        java.util.List<Instruction> calls = new java.util.ArrayList<>();
        while (it.hasNext()) {
            Instruction ins = it.next();
            if (!ins.getFlowType().isCall()) continue;
            for (Address t : ins.getFlows()) {
                Function c = currentProgram.getFunctionManager().getFunctionAt(t);
                Address real = c != null && c.isThunk() ? c.getThunkedFunction(true).getEntryPoint() : t;
                if (returning.contains(t) || returning.contains(real)) calls.add(ins);
            }
        }
        for (Instruction ins : calls) {
            ins.setFlowOverride(ghidra.program.model.listing.FlowOverride.NONE);
            ins.clearFallThroughOverride();
            Address next = ins.getMaxAddress().add(1);
            if (getInstructionAt(next) == null) disassemble(next);
            println("regrow " + f.getEntryPoint() + ": call at " + ins.getAddress() + " flow " + ins.getFlowType()
                    + " next " + (getInstructionAt(next) != null));
        }
        if (!calls.isEmpty()) CreateFunctionCmd.fixupFunctionBody(currentProgram, f, monitor);
        return f.getBody().getNumAddresses() > before;
    }

    @Override
    public void run() throws Exception {
        String[] a = getScriptArgs();
        DecompInterface ifc = new DecompInterface();
        ifc.openProgram(currentProgram);
        FunctionManager fm = currentProgram.getFunctionManager();
        String env = System.getenv("DECOMP_RETURNING");
        if (env != null && !env.isEmpty()) {
            for (String s : env.split(",")) {
                Address t = toAddr(s.trim().replaceFirst("^0x", ""));
                returning.add(t);
                Function c = fm.getFunctionAt(t);
                if (c != null) c.setNoReturn(false);
                // every thunk of it too
                for (Function g : fm.getFunctions(true))
                    if (g.isThunk() && g.getThunkedFunction(true).getEntryPoint().equals(t)) {
                        g.setNoReturn(false);
                        returning.add(g.getEntryPoint());
                    }
            }
        }
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
                for (int k = 0; k < 64 && !returning.isEmpty() && regrow(f); k++) { }
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
