package com.maskql.mask;

import com.maskql.nlp.EdsPseudoBridge;
import io.trino.spi.function.Description;
import io.trino.spi.function.ScalarFunction;
import io.trino.spi.function.SqlType;
import io.trino.spi.type.StandardTypes;
import io.trino.spi.TrinoException;
import io.trino.spi.StandardErrorCode;
import io.airlift.slice.Slice;
import io.airlift.slice.Slices;

import org.apache.pdfbox.text.PDFTextStripper;
import org.apache.pdfbox.pdmodel.PDDocument;
import java.io.IOException;

import org.bouncycastle.crypto.fpe.FPEFF1Engine;
import org.bouncycastle.crypto.params.KeyParameter;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.text.SimpleDateFormat;
import java.time.*;
import java.util.Base64;


public final class MaskUnstructured {
    
    @ScalarFunction(value = "text_pseudo", deterministic = false)
    @Description("Pseudonymize text using the legacy seed; prefer text_pseudo(text, seed)")
    @SqlType(StandardTypes.VARCHAR)
    public static Slice textPseudo(@SqlType(StandardTypes.VARCHAR) Slice input) {
        return textPseudo(input, Slices.utf8Slice("coucou"));
    }

    @ScalarFunction(value = "text_pseudo", deterministic = false)
    @Description("Pseudonymize text using an explicit seed or patient context")
    @SqlType(StandardTypes.VARCHAR)
    public static Slice textPseudo(
            @SqlType(StandardTypes.VARCHAR) Slice input,
            @SqlType(StandardTypes.VARCHAR) Slice seed) {
        if (input == null || seed == null) return null;
        String text = EdsPseudoBridge.getInstance().processOne(
                input.toStringUtf8(), seed.toStringUtf8());
        return Slices.utf8Slice(text);
    }

    @ScalarFunction("pdf_to_text")
    @Description("Extract plain text from a PDF binary")
    @SqlType(StandardTypes.VARBINARY)
    public static Slice pdfToText(@SqlType(StandardTypes.VARBINARY) Slice pdfBytes) {
        if (pdfBytes == null) return null;

        byte[] bytes = pdfBytes.getBytes();
        try (PDDocument doc = PDDocument.load(bytes)) {
            if (doc.isEncrypted()) {
                try {
                    doc.setAllSecurityToBeRemoved(true); // Try to allow extraction
                } catch (Exception e) {
                    return null;
                }
            }
            PDFTextStripper stripper = new PDFTextStripper();
            String text = stripper.getText(doc);
            if (text == null) return Slices.utf8Slice("");
            return Slices.utf8Slice(text.trim());
        } catch (IOException e) {
            return null;
        }
    }
}
