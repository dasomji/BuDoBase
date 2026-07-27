import * as React from "react"
import { Input as InputPrimitive } from "@base-ui/react/input"

import { cn } from "@/lib/utils"

const nativeControlClassName = "h-8 w-full min-w-0 rounded-lg border border-input bg-popover px-2.5 py-1 text-base text-foreground transition-colors outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:cursor-not-allowed disabled:bg-input/50 disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 min-[901px]:text-sm"

function Input({
  className,
  type,
  ...props
}) {
  return (
    <InputPrimitive
      type={type}
      data-slot="input"
      className={cn(
        nativeControlClassName,
        "file:inline-flex file:h-6 file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground",
        className
      )}
      {...props} />
  );
}

function NativeSelect({
  className,
  ...props
}) {
  return (
    <select
      data-slot="native-select"
      className={cn(nativeControlClassName, className)}
      {...props} />
  );
}

export { Input, NativeSelect }
