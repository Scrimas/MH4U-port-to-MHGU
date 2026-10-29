// Disassemble and create a function at every address listed in a text file (one hex address per line), so a
// stripped image (MHGU main32.elf) starts its analysis from known function starts.
// usage (headless, before analysis): -preScript MakeFuncs.java STARTS.txt
//@category MHF
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.mem.MemoryBlock;
import java.nio.file.Files;
import java.nio.file.Paths;

public class MakeFuncs extends GhidraScript {
    @Override
    public void run() throws Exception {
        int made = 0, skipped = 0;
        for (String line : Files.readAllLines(Paths.get(getScriptArgs()[0]))) {
            line = line.trim();
            if (line.isEmpty()) continue;
            Address a = toAddr(Long.parseLong(line, 16));
            MemoryBlock blk = currentProgram.getMemory().getBlock(a);
            if (blk == null || !blk.isExecute()) { skipped++; continue; }
            if (getFunctionAt(a) == null) {
                disassemble(a);
                if (createFunction(a, null) != null) made++;
            }
        }
        println("MakeFuncs: " + made + " functions created, " + skipped + " addresses outside code");
    }
}
