package com.maskql.mask;

import io.trino.spi.Plugin;
import java.util.Set;

public class MaskPlugin implements Plugin {
  @Override
  public Set<Class<?>> getFunctions() {
    return Set.of(MaskFunctions.class);
  }
}
