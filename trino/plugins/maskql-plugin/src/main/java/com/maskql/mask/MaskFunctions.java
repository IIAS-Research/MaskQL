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

import org.jasypt.util.text.AES256TextEncryptor;

public final class MaskFunctions {
    private static final AES256TextEncryptor ENCRYPTOR = new AES256TextEncryptor();

    static {
        String pwd = System.getenv("TEXT_ENCRYPT_PASSWORD");
        if (pwd == null || pwd.isEmpty()) {
            throw new IllegalStateException(
                "Missing environment variable TEXT_ENCRYPT_PASSWORD for Jasypt AES256TextEncryptor"
            );
        }
        ENCRYPTOR.setPassword(pwd);
    }

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

    @ScalarFunction("text_encrypt")
    @Description("Encrypt a VARCHAR using Jasypt AES-256 (CBC+salt+IV). Password from env TEXT_ENCRYPT_PASSWORD. Returns Base64 text.")
    @SqlType(StandardTypes.VARCHAR)
    public static Slice textEncrypt(@SqlType(StandardTypes.VARCHAR) Slice input) {
        if (input == null) return null;

        try {
            return Slices.utf8Slice(ENCRYPTOR.encrypt(input.toStringUtf8()));
        } catch (Exception e) {
            throw new TrinoException(StandardErrorCode.GENERIC_INTERNAL_ERROR, "AES encryption failed", e);
        }
    }
}
