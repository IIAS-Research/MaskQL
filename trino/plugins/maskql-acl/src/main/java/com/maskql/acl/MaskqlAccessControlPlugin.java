package com.maskql.acl;

import io.trino.spi.Plugin;
import io.trino.spi.security.SystemAccessControlFactory;
import java.util.List;

public class MaskqlAccessControlPlugin implements Plugin {
    @Override
    public Iterable<SystemAccessControlFactory> getSystemAccessControlFactories() {
        return List.of(new MaskqlSystemAccessControlFactory());
    }
}
