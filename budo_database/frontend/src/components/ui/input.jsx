import * as React from "react"
import { Input as InputPrimitive } from "@base-ui/react/input"
import { ChevronDown } from "lucide-react"

import { cn } from "@/lib/utils"

const nativeControlClassName = "h-8 w-full min-w-0 rounded-lg border border-input bg-popover px-2.5 py-1 text-base text-foreground transition-colors outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring disabled:pointer-events-none disabled:cursor-not-allowed disabled:bg-muted disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 min-[901px]:text-sm"

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
  multiple,
  size,
  ...props
}) {
  const showIndicator = !multiple && (size == null || Number(size) <= 1);
  return (
    <span className="relative block w-full" data-slot="native-select-control">
      <select
        data-slot="native-select"
        className={cn(
          nativeControlClassName,
          showIndicator && "peer appearance-none pr-10",
          className
        )}
        multiple={multiple}
        size={size}
        {...props} />
      {showIndicator && (
        <ChevronDown
          className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-muted-foreground peer-disabled:opacity-50"
          aria-hidden="true" />
      )}
    </span>
  );
}

function Textarea({
  className,
  ...props
}) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(nativeControlClassName, "h-auto", className)}
      {...props} />
  );
}

export { Input, NativeSelect, Textarea }
