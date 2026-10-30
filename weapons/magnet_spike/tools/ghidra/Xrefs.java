// Print the instructions that reach the given data addresses through GU's PC-relative pairs
// (ldr rX, [pc, #imm] holding L, then add rY, pc, rX or ldr rY, [pc, rX] at A: target A + 8 + L), each with its
// function's entry. A target matches when it lies in [ADDR, ADDR + SPAN).
// usage (headless): -process main32.elf -noanalysis -readOnly -postScript Xrefs.java OUT.txt SPAN ADDR...
//@category MHF
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import java.io.FileWriter;
import java.io.PrintWriter;

public class Xrefs extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] a = getScriptArgs();
        long span = Long.decode(a[1]);
        long[] want = new long[a.length - 2];
        for (int i = 2; i < a.length; i++) want[i - 2] = Long.decode(a[i]);
        PrintWriter out = new PrintWriter(new FileWriter(a[0]));
        InstructionIterator it = currentProgram.getListing().getInstructions(true);
        java.util.Map<String, Long> lit = new java.util.HashMap<>();
        java.util.Map<String, Long> at = new java.util.HashMap<>();
        while (it.hasNext() && !monitor.isCancelled()) {
            Instruction ins = it.next();
            String m = ins.getMnemonicString().toLowerCase();
            long pc = ins.getAddress().getOffset();
            if (ins.getNumOperands() < 2) continue;
            String r0 = ins.getDefaultOperandRepresentation(0);
            String r1 = ins.getDefaultOperandRepresentation(1);
            if (m.equals("ldr") && !r1.startsWith("[pc,") && ins.getReferencesFrom().length > 0
                    && ins.getReferencesFrom()[0].getReferenceType().isRead() && r1.startsWith("[0x")) {
                Address l = ins.getReferencesFrom()[0].getToAddress();
                lit.put(r0, currentProgram.getMemory().getInt(l) & 0xffffffffL);
                at.put(r0, pc);
                continue;
            }
            String rx = null;
            if (m.startsWith("add") && ins.getNumOperands() == 3 && r1.equals("pc")) rx = ins.getDefaultOperandRepresentation(2);
            if (m.startsWith("ldr") && r1.startsWith("[pc,")) rx = r1.substring(4, r1.length() - 1);
            if (rx == null || !lit.containsKey(rx) || pc - at.get(rx) > 64) continue;
            long t = (pc + 8 + lit.get(rx)) & 0xffffffffL;
            for (long w : want) {
                if (t < w || t >= w + span) continue;
                Function f = currentProgram.getFunctionManager().getFunctionContaining(ins.getAddress());
                out.printf("%08x -> %08x (+%d) in %s%n", pc, t, t - w, f == null ? "?" : f.getEntryPoint());
            }
        }
        out.close();
    }
}
