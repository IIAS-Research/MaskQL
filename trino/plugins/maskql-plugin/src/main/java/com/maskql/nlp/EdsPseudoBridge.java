package com.maskql.nlp;

import jep.SharedInterpreter;

import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

public final class EdsPseudoBridge {
    private static final String PIPELINE_DIR = System.getenv().getOrDefault(
            "EDS_PIPELINE_DIR", "/opt/models/eds-pseudo-public");
    private static final EdsPseudoBridge INSTANCE = new EdsPseudoBridge();

    private final ExecutorService worker;
    private Future<?> initialization;
    private volatile Thread workerThread;
    // Only the dedicated worker may create, use or close this JEP interpreter.
    private SharedInterpreter interpreter;

    private EdsPseudoBridge() {
        worker = Executors.newSingleThreadExecutor(task -> {
            Thread thread = new Thread(() -> {
                try {
                    task.run();
                } finally {
                    if (interpreter != null) {
                        interpreter.close();
                    }
                }
            }, "eds-pseudo-worker");
            thread.setDaemon(true);
            workerThread = thread;
            return thread;
        });
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            worker.shutdown();
            try {
                Thread thread = workerThread;
                if (thread != null) {
                    // Join the thread, including its interpreter-close block.
                    thread.join(10_000);
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }, "eds-pseudo-shutdown"));
    }

    public static EdsPseudoBridge getInstance() {
        return INSTANCE;
    }

    /** Called by the plugin before Trino reports that startup is complete. */
    public void initialize() {
        Future<?> ready;
        synchronized (this) {
            if (initialization == null) {
                // Submit only after class initialization has completed: waiting
                // for this worker in a static initializer would deadlock JEP.
                initialization = worker.submit(this::loadPipeline);
            }
            ready = initialization;
        }
        await(ready, false);
    }

    private void loadPipeline() {
        System.err.println("[EdsPseudoBridge] Loading EDS pipeline");
        interpreter = new SharedInterpreter();
        interpreter.set("PIPE", PIPELINE_DIR);
        interpreter.runScript("/app/load_edspseudo.py");
        Object error = interpreter.getValue("_ERR");
        if (error != null) {
            throw new IllegalStateException("EDS pipeline init failed:\n" + error);
        }
        interpreter.invoke("_process_text", "warmup", "seed");
        System.err.println("[EdsPseudoBridge] EDS pipeline ready");
    }

    public String processOne(String text, String seed) {
        initialize();
        // One model per node; serialize calls to preserve JEP thread ownership
        // and prevent concurrent calls from sharing mutable seed/model state.
        return await(worker.submit(() ->
                (String) interpreter.invoke("_process_text", text, seed)), true);
    }

    private static <T> T await(Future<T> result, boolean cancelOnInterrupt) {
        try {
            return result.get();
        } catch (InterruptedException e) {
            if (cancelOnInterrupt) {
                result.cancel(false);
            }
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Interrupted while waiting for the EDS pipeline", e);
        } catch (ExecutionException e) {
            Throwable cause = e.getCause();
            if (cause instanceof RuntimeException runtimeException) {
                throw runtimeException;
            }
            if (cause instanceof Error error) {
                throw error;
            }
            throw new IllegalStateException("EDS pipeline execution failed", cause);
        }
    }
}
