function classes(...values) {
  return values.filter(Boolean).join(' ');
}

export function TableScroll({
  children,
  className = '',
  stickyHeader = false,
  stickyFirstColumn = false,
  verticalScroll = false,
  ...props
}) {
  return (
    <div
      className={classes('table-container', className)}
      data-slot="table-scroll"
      data-sticky-header={stickyHeader ? '' : undefined}
      data-sticky-first-column={stickyFirstColumn ? '' : undefined}
      data-vertical-scroll={verticalScroll ? '' : undefined}
      {...props}
    >
      {children}
    </div>
  );
}

export function Table({ children, className = '', ...props }) {
  return <table className={classes('data-table', className)} data-slot="table" {...props}>{children}</table>;
}

export function TableHeader({ children, className = '', ...props }) {
  return <thead className={className} data-slot="table-header" {...props}>{children}</thead>;
}

export function TableBody({ children, className = '', ...props }) {
  return <tbody className={className} data-slot="table-body" {...props}>{children}</tbody>;
}

export function TableRow({ children, className = '', ...props }) {
  return <tr className={className} data-slot="table-row" {...props}>{children}</tr>;
}

export function TableHead({ children, className = '', ...props }) {
  return <th className={className} data-slot="table-head" {...props}>{children}</th>;
}

export function TableCell({ children, className = '', ...props }) {
  return <td className={className} data-slot="table-cell" {...props}>{children}</td>;
}
