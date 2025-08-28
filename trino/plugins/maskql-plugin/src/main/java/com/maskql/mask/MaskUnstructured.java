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
    
    private static final EdsPseudoBridge BRIDGE = EdsPseudoBridge.getInstance();


    @ScalarFunction("text_pseudo")
    @Description("Replace identifying entities in texts by fake placeholders")
    @SqlType(StandardTypes.VARCHAR)
    public static Slice textPseudo(@SqlType(StandardTypes.VARCHAR) Slice input) {
        if (input == null) return null;
        String json = BRIDGE.processOne(input.toStringUtf8());
        return Slices.utf8Slice(json);
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
