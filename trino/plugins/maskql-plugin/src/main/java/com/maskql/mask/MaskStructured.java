package com.maskql.mask;

import io.airlift.slice.Slice;
import io.airlift.slice.Slices;
import io.trino.spi.function.Description;
import io.trino.spi.function.ScalarFunction;
import io.trino.spi.function.SqlType;
import io.trino.spi.type.StandardTypes;
import io.trino.spi.function.LiteralParameters;

import java.util.Base64;

public final class MaskStructured {

    // VARCHAR //
    @ScalarFunction("encrypt")
    @Description("Encrypt VARCHAR with env password; returns base64(nonce||ciphertext)")
    @SqlType(StandardTypes.VARCHAR)
    public static Slice encryptVarchar(@SqlType(StandardTypes.VARCHAR) Slice value) {
        if (value == null) return null;
        byte[] ct = MaskCrypto.encryptDeterministicBytes(value.getBytes(), MaskCrypto.DOMAIN_VARCHAR);
        return Slices.utf8Slice(Base64.getEncoder().encodeToString(ct));
    }

    @ScalarFunction("decrypt")
    @Description("Decrypt VARCHAR produced by encrypt(VARCHAR)")
    @SqlType(StandardTypes.VARCHAR)
    public static Slice decryptVarchar(@SqlType(StandardTypes.VARCHAR) Slice valueBase64) {
        if (valueBase64 == null) return null;
        byte[] all = Base64.getDecoder().decode(valueBase64.toStringUtf8());
        byte[] pt = MaskCrypto.decryptDeterministicBytes(all, MaskCrypto.DOMAIN_VARCHAR);
        return Slices.wrappedBuffer(pt);
    }

    //  VARBINARY
    @ScalarFunction("encrypt")
    @Description("Encrypt VARBINARY with env password; returns nonce||ciphertext (VARBINARY)")
    @SqlType(StandardTypes.VARBINARY)
    public static Slice encryptVarbinary(@SqlType(StandardTypes.VARBINARY) Slice value) {
        if (value == null) return null;
        byte[] ct = MaskCrypto.encryptDeterministicBytes(value.getBytes(), MaskCrypto.DOMAIN_VARBINARY);
        return Slices.wrappedBuffer(ct);
    }

    @ScalarFunction("decrypt")
    @Description("Decrypt VARBINARY produced by encrypt(VARBINARY)")
    @SqlType(StandardTypes.VARBINARY)
    public static Slice decryptVarbinary(@SqlType(StandardTypes.VARBINARY) Slice value) {
        if (value == null) return null;
        byte[] pt = MaskCrypto.decryptDeterministicBytes(value.getBytes(), MaskCrypto.DOMAIN_VARBINARY);
        return Slices.wrappedBuffer(pt);
    }

    //  BIGINT (carrier: long)
    @ScalarFunction("encrypt")
    @Description("Encrypt BIGINT with env password (format-preserving on 64-bit space)")
    @SqlType(StandardTypes.BIGINT)
    public static long encryptBigint(@SqlType(StandardTypes.BIGINT) long x) {
        return MaskCrypto.prp64Encrypt(x, MaskCrypto.DOMAIN_BIGINT);
    }
    @ScalarFunction("decrypt")
    @Description("Decrypt BIGINT with env password")
    @SqlType(StandardTypes.BIGINT)
    public static long decryptBigint(@SqlType(StandardTypes.BIGINT) long x) {
        return MaskCrypto.prp64Decrypt(x, MaskCrypto.DOMAIN_BIGINT);
    }

    //  INTEGER (carrier: long)
    @ScalarFunction("encrypt")
    @Description("Encrypt INTEGER with env password (format-preserving)")
    @SqlType(StandardTypes.INTEGER)
    public static long encryptInteger(@SqlType(StandardTypes.INTEGER) long x) {
        int xi = (int) x;
        int out = MaskCrypto.prp32Encrypt(xi, MaskCrypto.DOMAIN_INTEGER);
        return (long) out; // Trino attend un long carrier pour INTEGER
    }
    @ScalarFunction("decrypt")
    @Description("Decrypt INTEGER with env password")
    @SqlType(StandardTypes.INTEGER)
    public static long decryptInteger(@SqlType(StandardTypes.INTEGER) long x) {
        int xi = (int) x;
        int out = MaskCrypto.prp32Decrypt(xi, MaskCrypto.DOMAIN_INTEGER);
        return (long) out;
    }

    //  SMALLINT (carrier: long)
    @ScalarFunction("encrypt")
    @Description("Encrypt SMALLINT with env password (format-preserving)")
    @SqlType(StandardTypes.SMALLINT)
    public static long encryptSmallint(@SqlType(StandardTypes.SMALLINT) long x) {
        short xs = (short) x;
        short out = MaskCrypto.prp16Encrypt(xs, MaskCrypto.DOMAIN_SMALLINT);
        return (long) out; // carrier long
    }
    @ScalarFunction("decrypt")
    @Description("Decrypt SMALLINT with env password")
    @SqlType(StandardTypes.SMALLINT)
    public static long decryptSmallint(@SqlType(StandardTypes.SMALLINT) long x) {
        short xs = (short) x;
        short out = MaskCrypto.prp16Decrypt(xs, MaskCrypto.DOMAIN_SMALLINT);
        return (long) out;
    }

    //  TINYINT (carrier: long)
    @ScalarFunction("encrypt")
    @Description("Encrypt TINYINT with env password (format-preserving)")
    @SqlType(StandardTypes.TINYINT)
    public static long encryptTinyint(@SqlType(StandardTypes.TINYINT) long x) {
        byte xb = (byte) x;
        byte out = MaskCrypto.prp8Encrypt(xb, MaskCrypto.DOMAIN_TINYINT);
        return (long) out;
    }
    @ScalarFunction("decrypt")
    @Description("Decrypt TINYINT with env password")
    @SqlType(StandardTypes.TINYINT)
    public static long decryptTinyint(@SqlType(StandardTypes.TINYINT) long x) {
        byte xb = (byte) x;
        byte out = MaskCrypto.prp8Decrypt(xb, MaskCrypto.DOMAIN_TINYINT);
        return (long) out;
    }

    //  DOUBLE (carrier: double)
    @ScalarFunction("encrypt")
    @Description("Encrypt DOUBLE with env password (bitwise bijection; preserves type)")
    @SqlType(StandardTypes.DOUBLE)
    public static double encryptDouble(@SqlType(StandardTypes.DOUBLE) double v) {
        long bits = Double.doubleToRawLongBits(v);
        long out = MaskCrypto.prp64Encrypt(bits, MaskCrypto.DOMAIN_DOUBLE);
        return Double.longBitsToDouble(out);
    }
    @ScalarFunction("decrypt")
    @Description("Decrypt DOUBLE with env password")
    @SqlType(StandardTypes.DOUBLE)
    public static double decryptDouble(@SqlType(StandardTypes.DOUBLE) double v) {
        long bits = Double.doubleToRawLongBits(v);
        long out = MaskCrypto.prp64Decrypt(bits, MaskCrypto.DOMAIN_DOUBLE);
        return Double.longBitsToDouble(out);
    }

    //  REAL (carrier: long = int bits du float)
    @ScalarFunction("encrypt")
    @Description("Encrypt REAL with env password (bitwise bijection)")
    @SqlType(StandardTypes.REAL)
    public static long encryptReal(@SqlType(StandardTypes.REAL) long valueBits) {
        int bits = (int) valueBits;
        int out = MaskCrypto.prp32Encrypt(bits, MaskCrypto.DOMAIN_REAL);
        return out & 0xFFFF_FFFFL; // repack in a long
    }
    @ScalarFunction("decrypt")
    @Description("Decrypt REAL with env password")
    @SqlType(StandardTypes.REAL)
    public static long decryptReal(@SqlType(StandardTypes.REAL) long valueBits) {
        int bits = (int) valueBits;
        int out = MaskCrypto.prp32Decrypt(bits, MaskCrypto.DOMAIN_REAL);
        return out & 0xFFFF_FFFFL;
    }

    //  BOOLEAN (carrier: boolean)
    @ScalarFunction("encrypt")
    @Description("Encrypt BOOLEAN with env password (bijection true/false)")
    @SqlType(StandardTypes.BOOLEAN)
    public static boolean encryptBoolean(@SqlType(StandardTypes.BOOLEAN) boolean v) {
        byte enc = MaskCrypto.prp8Encrypt((byte) (v ? 1 : 0), MaskCrypto.DOMAIN_BOOLEAN);
        return (enc & 0x01) == 1;
    }
    @ScalarFunction("decrypt")
    @Description("Decrypt BOOLEAN with env password")
    @SqlType(StandardTypes.BOOLEAN)
    public static boolean decryptBoolean(@SqlType(StandardTypes.BOOLEAN) boolean v) {
        byte dec = MaskCrypto.prp8Decrypt((byte) (v ? 1 : 0), MaskCrypto.DOMAIN_BOOLEAN);
        return (dec & 0x01) == 1;
    }

    //  DATE
    @ScalarFunction("encrypt")
    @Description("Encrypt DATE with env password (format-preserving on 32-bit days)")
    @SqlType(StandardTypes.DATE)
    public static long encryptDate(@SqlType(StandardTypes.DATE) long daysSinceEpoch) {
        int x = (int) daysSinceEpoch;
        return (long) MaskCrypto.prp32Encrypt(x, MaskCrypto.DOMAIN_DATE);
    }
    @ScalarFunction("decrypt")
    @Description("Decrypt DATE with env password")
    @SqlType(StandardTypes.DATE)
    public static long decryptDate(@SqlType(StandardTypes.DATE) long daysSinceEpoch) {
        int x = (int) daysSinceEpoch;
        return (long) MaskCrypto.prp32Decrypt(x, MaskCrypto.DOMAIN_DATE);
    }

    //  TIMESTAMP
    @ScalarFunction("encrypt")
    @LiteralParameters("p")
    @Description("Encrypt TIMESTAMP(p) with env password (p ≤ 6, 64-bit epoch micros)")
    @SqlType("timestamp(p)")
    public static long encryptTimestamp(@SqlType("timestamp(p)") long epochMicros) {
        return MaskCrypto.prp64Encrypt(epochMicros, MaskCrypto.DOMAIN_TIMESTAMP);
    }

    @ScalarFunction("decrypt")
    @LiteralParameters("p")
    @Description("Decrypt TIMESTAMP(p) with env password (p ≤ 6)")
    @SqlType("timestamp(p)")
    public static long decryptTimestamp(@SqlType("timestamp(p)") long epochMicros) {
        return MaskCrypto.prp64Decrypt(epochMicros, MaskCrypto.DOMAIN_TIMESTAMP);
    }
}
