package com.maskql.nlp;

import jep.SharedInterpreter;

import java.util.Objects;
import java.util.concurrent.ConcurrentLinkedQueue;

public final class EdsPseudoBridge {
    private static final String PIPELINE_DIR = System.getenv().getOrDefault("EDS_PIPELINE_DIR", "/usr/lib/trino/models/eds-pseudo-public");
    private static final ConcurrentLinkedQueue<SharedInterpreter> REGISTRY = new ConcurrentLinkedQueue<>();
    private static final EdsPseudoBridge INSTANCE = new EdsPseudoBridge();

    private final ThreadLocal<SharedInterpreter> tl = ThreadLocal.withInitial(() -> {
        SharedInterpreter py = new SharedInterpreter();
        String pipe = escapePy(PIPELINE_DIR);

        // Init python
        // Load method "_process_text(text)" 
        py.exec(
            "PIPE = '" + pipe + "'\n" +
            "with open(\"/app/load_edspseudo.py\") as f:" +
            "    code = f.read()\n" +
            "exec(code)\n"
        );

        // Catch error, impossible to debug without that
        Object err = py.getValue("_ERR");
        if (err != null && !"None".equals(String.valueOf(err))) {
            System.err.println("[EdsPseudoBridge] Python init failed:\n" + err);
            
            throw new RuntimeException("EDS pipeline init failed");
        }

        REGISTRY.add(py);
        return py;
    });

    private EdsPseudoBridge() {
        try {
            SharedInterpreter py = tl.get();
            py.exec("_ = _process_text('warmup', 'seed')");
        } catch (Throwable t) {
            System.err.println("[EdsPseudoBridge] Warm-up failed: " + t);
        }

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            for (SharedInterpreter py : REGISTRY) {
                try { py.close(); } catch (Throwable ignored) {}
            }
            REGISTRY.clear();
        }, "eds-pseudo-shutdown"));
    }

    public static EdsPseudoBridge getInstance() { return INSTANCE; }

    public String processOne(String text) {
        SharedInterpreter py = tl.get();
        py.set("input", text);
        py.set("seed", "coucou");
        py.exec("res_json = _process_text(input, seed)");
        return (String) py.getValue("res_json");
    }

    private static String escapePy(String s) {
        return s.replace("\\", "\\\\").replace("'", "\\'");
    }
}