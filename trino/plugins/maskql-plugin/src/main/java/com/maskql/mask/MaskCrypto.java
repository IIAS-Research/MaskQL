package com.maskql.mask;

import io.airlift.slice.Slice;
import io.airlift.slice.Slices;
import io.trino.spi.TrinoException;
import io.trino.spi.StandardErrorCode;
import io.trino.spi.function.Description;
import io.trino.spi.function.ScalarFunction;
import io.trino.spi.function.SqlType;
import io.trino.spi.type.StandardTypes;

import javax.crypto.Cipher;
import javax.crypto.Mac;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.PBEKeySpec;
import javax.crypto.spec.SecretKeySpec;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.util.Arrays;
import java.util.Base64;

import org.apache.pdfbox.text.PDFTextStripper;
import org.apache.pdfbox.pdmodel.PDDocument;
import java.io.IOException;


class MaskCrypto {
    // Domain labels
    static final String DOMAIN_VARCHAR   = "VARCHAR";
    static final String DOMAIN_VARBINARY = "VARBINARY";
    static final String DOMAIN_BIGINT    = "BIGINT";
    static final String DOMAIN_INTEGER   = "INTEGER";
    static final String DOMAIN_SMALLINT  = "SMALLINT";
    static final String DOMAIN_TINYINT   = "TINYINT";
    static final String DOMAIN_DOUBLE    = "DOUBLE";
    static final String DOMAIN_REAL      = "REAL";
    static final String DOMAIN_BOOLEAN   = "BOOLEAN";
    static final String DOMAIN_DATE      = "DATE";
    static final String DOMAIN_TIMESTAMP = "TIMESTAMP";

    private static final int PBKDF2_ITER = 200000; // Number of derivation of the key
    private static final int AES_KEY_BITS = 256; // AES key size
    private static final int GCM_TAG_BITS = 128; // Tag size for GCM

    private static final byte[] STATIC_SALT = "trino-mask-default-salt-v1".getBytes(StandardCharsets.UTF_8); // Default salt

    private static final SecretKeySpec MASTER_KEY; // Derived key from password
    private static final String CONTEXT; // Global MaskQL context

    static {
        String secret = System.getenv("ENCRYPT_PASSWORD");
        if (secret == null || secret.isEmpty()) {
            throw new TrinoException(StandardErrorCode.GENERIC_USER_ERROR, "ENCRYPT_PASSWORD environment variable is required");
        }
        CONTEXT = System.getenv().getOrDefault("MASKQL_CONTEXT", "default");
        MASTER_KEY = deriveAesKey(secret, CONTEXT);
    }

    private static SecretKeySpec deriveAesKey(String password, String context) {
        try {
            byte[] salt = hmacSha256(STATIC_SALT, context);
            PBEKeySpec spec = new PBEKeySpec(password.toCharArray(), salt, PBKDF2_ITER, AES_KEY_BITS);
            SecretKeyFactory skf = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256");
            byte[] key = skf.generateSecret(spec).getEncoded();
            return new SecretKeySpec(key, "AES");
        } catch (GeneralSecurityException e) {
            throw new TrinoException(StandardErrorCode.GENERIC_INTERNAL_ERROR, "Key derivation failed", e);
        }
    }

    // AES-GCM
    static byte[] encryptDeterministicBytes(byte[] plaintext, String domain) {
        try {
            byte[] dom = domainWithContext(domain);
            byte[] nonce = Arrays.copyOf(hmacSha256(MASTER_KEY, concat(dom, plaintext)), 12);
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            GCMParameterSpec spec = new GCMParameterSpec(GCM_TAG_BITS, nonce);
            cipher.init(Cipher.ENCRYPT_MODE, MASTER_KEY, spec);
            cipher.updateAAD(dom);
            byte[] ciphertext = cipher.doFinal(plaintext);
            return concat(nonce, ciphertext);
        } catch (GeneralSecurityException e) {
            throw new TrinoException(StandardErrorCode.GENERIC_INTERNAL_ERROR, "AES-GCM encryption failed", e);
        }
    }

    static byte[] decryptDeterministicBytes(byte[] nonceAndCiphertext, String domain) {
        try {
            if (nonceAndCiphertext.length < 12 + 16) {
                throw new TrinoException(StandardErrorCode.GENERIC_USER_ERROR, "Ciphertext too short");
            }
            byte[] nonce = Arrays.copyOfRange(nonceAndCiphertext, 0, 12);
            byte[] ciphertext = Arrays.copyOfRange(nonceAndCiphertext, 12, nonceAndCiphertext.length);
            byte[] dom = domainWithContext(domain);
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            GCMParameterSpec spec = new GCMParameterSpec(GCM_TAG_BITS, nonce);
            cipher.init(Cipher.DECRYPT_MODE, MASTER_KEY, spec);
            cipher.updateAAD(dom);
            return cipher.doFinal(ciphertext);
        } catch (GeneralSecurityException e) {
            throw new TrinoException(StandardErrorCode.GENERIC_USER_ERROR, "AES-GCM decryption failed (wrong secret/context or corrupted data)", e);
        }
    }

    // PRP Feistel (HMAC-SHA-256)
    static long prp64Encrypt(long x, String domain) {
        int L = (int)(x >>> 32);
        int R = (int)(x & 0xFFFFFFFFL);
        for (int i = 0; i < 8; i++) {
            byte[] f = prf(domain, R, i, (byte)0xE1);
            int f32 = ByteBuffer.wrap(f).order(ByteOrder.BIG_ENDIAN).getInt();
            int newL = R;
            int newR = L ^ f32;
            L = newL;
            R = newR;
        }
        return ((long)L << 32) | (R & 0xFFFFFFFFL);
    }
    static long prp64Decrypt(long x, String domain) {
        int L = (int)(x >>> 32);
        int R = (int)(x & 0xFFFFFFFFL);
        for (int i = 7; i >= 0; i--) {
            byte[] f = prf(domain, L, i, (byte)0xE1);
            int f32 = ByteBuffer.wrap(f).order(ByteOrder.BIG_ENDIAN).getInt();
            int newR = L;
            int newL = R ^ f32;
            R = newR;
            L = newL;
        }
        return ((long)L << 32) | (R & 0xFFFFFFFFL);
    }

    static int prp32Encrypt(int x, String domain) {
        short L = (short)((x >>> 16) & 0xFFFF);
        short R = (short)(x & 0xFFFF);
        for (int i = 0; i < 8; i++) {
            byte[] f = prf(domain, R & 0xFFFF, i, (byte)0xE2);
            short f16 = (short)(ByteBuffer.wrap(f).order(ByteOrder.BIG_ENDIAN).getShort() & 0xFFFF);
            short newL = R;
            short newR = (short)(L ^ f16);
            L = newL;
            R = newR;
        }
        return ((L & 0xFFFF) << 16) | (R & 0xFFFF);
    }
    static int prp32Decrypt(int x, String domain) {
        short L = (short)((x >>> 16) & 0xFFFF);
        short R = (short)(x & 0xFFFF);
        for (int i = 7; i >= 0; i--) {
            byte[] f = prf(domain, L & 0xFFFF, i, (byte)0xE2);
            short f16 = (short)(ByteBuffer.wrap(f).order(ByteOrder.BIG_ENDIAN).getShort() & 0xFFFF);
            short newR = L;
            short newL = (short)(R ^ f16);
            R = newR;
            L = newL;
        }
        return ((L & 0xFFFF) << 16) | (R & 0xFFFF);
    }

    static short prp16Encrypt(short x, String domain) {
        int L = (x >>> 8) & 0xFF;
        int R = x & 0xFF;
        for (int i = 0; i < 8; i++) {
            byte[] f = prf(domain, R & 0xFF, i, (byte)0xE3);
            int f8 = f[0] & 0xFF;
            int newL = R;
            int newR = L ^ f8;
            L = newL & 0xFF;
            R = newR & 0xFF;
        }
        return (short)((L << 8) | (R & 0xFF));
    }
    static short prp16Decrypt(short x, String domain) {
        int L = (x >>> 8) & 0xFF;
        int R = x & 0xFF;
        for (int i = 7; i >= 0; i--) {
            byte[] f = prf(domain, L & 0xFF, i, (byte)0xE3);
            int f8 = f[0] & 0xFF;
            int newR = L;
            int newL = R ^ f8;
            R = newR & 0xFF;
            L = newL & 0xFF;
        }
        return (short)((L << 8) | (R & 0xFF));
    }

    static byte prp8Encrypt(byte x, String domain) {
        int L = (x >>> 4) & 0x0F;
        int R = x & 0x0F;
        for (int i = 0; i < 8; i++) {
            byte[] f = prf(domain, R & 0x0F, i, (byte)0xE4);
            int f4 = (f[0] & 0xFF) & 0x0F;
            int newL = R;
            int newR = L ^ f4;
            L = newL & 0x0F;
            R = newR & 0x0F;
        }
        return (byte)((L << 4) | (R & 0x0F));
    }
    static byte prp8Decrypt(byte x, String domain) {
        int L = (x >>> 4) & 0x0F;
        int R = x & 0x0F;
        for (int i = 7; i >= 0; i--) {
            byte[] f = prf(domain, L & 0x0F, i, (byte)0xE4);
            int f4 = (f[0] & 0xFF) & 0x0F;
            int newR = L;
            int newL = R ^ f4;
            R = newR & 0x0F;
            L = newL & 0x0F;
        }
        return (byte)((L << 4) | (R & 0x0F));
    }

    // PRF HMAC-SHA256
    private static byte[] prf(String domain, int half, int round, byte sep) {
        byte[] dom = domainWithContext(domain);
        ByteBuffer buf = ByteBuffer.allocate(dom.length + 4 + 4 + 1);
        buf.put(dom);
        buf.putInt(half);
        buf.putInt(round);
        buf.put(sep);
        return hmacSha256(MASTER_KEY, buf.array());
    }

    private static byte[] domainWithContext(String domain) {
        return (CONTEXT + "::" + domain).getBytes(StandardCharsets.UTF_8);
    }

    // HMAC utils
    private static byte[] hmacSha256(SecretKeySpec key, byte[] data) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(key.getEncoded(), "HmacSHA256"));
            return mac.doFinal(data);
        } catch (GeneralSecurityException e) {
            throw new TrinoException(StandardErrorCode.GENERIC_INTERNAL_ERROR, "HMAC failed", e);
        }
    }
    private static byte[] hmacSha256(byte[] key, String data) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(key, "HmacSHA256"));
            return mac.doFinal(data.getBytes(StandardCharsets.UTF_8));
        } catch (GeneralSecurityException e) {
            throw new TrinoException(StandardErrorCode.GENERIC_INTERNAL_ERROR, "HMAC failed", e);
        }
    }

    // small helper
    static byte[] concat(byte[] a, byte[] b) {
        byte[] out = Arrays.copyOf(a, a.length + b.length);
        System.arraycopy(b, 0, out, a.length, b.length);
        return out;
    }
}
