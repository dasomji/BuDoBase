import * as React from "react"

const MOBILE_BREAKPOINT = 901
const MOBILE_QUERY = `(max-width: ${MOBILE_BREAKPOINT - 1}px)`

function readIsMobile() {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return false
  }
  return window.matchMedia(MOBILE_QUERY).matches
}

export function useIsMobile() {
  const [isMobile, setIsMobile] = React.useState(readIsMobile)

  React.useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return undefined

    const mql = window.matchMedia(MOBILE_QUERY)
    const onChange = event => setIsMobile(event.matches)
    mql.addEventListener("change", onChange)
    return () => mql.removeEventListener("change", onChange)
  }, [])

  return isMobile
}
