package com.maskql.mask;

import io.trino.spi.function.Description;
import io.trino.spi.function.ScalarFunction;
import io.trino.spi.function.SqlType;
import io.trino.spi.type.StandardTypes;
import io.airlift.slice.Slice;
import io.airlift.slice.Slices;

public final class MaskFunctions {
    @ScalarFunction("text_pseudo")
    @Description("Replace identifying entities in texts by fake placeholders")
    @SqlType(StandardTypes.VARCHAR)
    public static Slice textPseudo(@SqlType(StandardTypes.VARCHAR) Slice input) {
        if (input == null) {
            return null;
        }
        String text = input.toStringUtf8();
        
        // Basic first try
        if (text.length() < 3) return Slices.utf8Slice("***");

        String out = text.substring(0, 2) + "*".repeat(Math.max(3, text.length()));
        return Slices.utf8Slice(out);
    }
}
