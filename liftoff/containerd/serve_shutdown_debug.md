
# Diagnosing `Serve()` Hanging in Go Tests — Accept() Race

This guide explains how to diagnose and debug race conditions in Go server code where `Serve()` may hang on `Accept()` due to an immediate shutdown (as seen in containerd/ttrpc PR #175).

---

## 🔍 Common Scenario: Race Between `Serve()` and `Shutdown()`

In test environments, if `Shutdown()` is called right after `Serve()` is launched in a goroutine, the server may:

- Close the listener before `Serve()` starts calling `Accept()`
- Cause `Serve()` to block forever, waiting on `Accept()` with no available connection or error

---

## 🧪 Method 1: Use `kill -QUIT` or `kill -3` to Dump Goroutines

1. Run your test:
   ```bash
   go test -v ./your/package -run TestRace
   ```

2. When test hangs, find the PID:
   ```bash
   ps aux | grep test
   ```

3. Trigger goroutine dump:
   ```bash
   kill -QUIT <pid>
   ```

4. Look for output like:
   ```
   goroutine 27 [IO wait]:
   net.(*TCPListener).Accept(...)
   github.com/containerd/ttrpc.(*Server).Serve(...)
   ```

---

## 🧪 Method 2: Use `runtime/pprof` in Test Code

Insert into your test:
```go
import (
    "runtime/pprof"
    "os"
)

func dumpStacks() {
    pprof.Lookup("goroutine").WriteTo(os.Stdout, 2)
}
```

Call it after `Shutdown()`:
```go
time.Sleep(2 * time.Second)
dumpStacks()
```

---

## 🧪 Method 3: Use HTTP `pprof` Web UI for Long-running Programs

In your server code:
```go
import _ "net/http/pprof"
import "net/http"

func init() {
    go http.ListenAndServe("localhost:6060", nil)
}
```

Then access:
```
http://localhost:6060/debug/pprof/goroutine?debug=2
```

---

## ✅ Best Practice for ttrpc or containerd tests

For race conditions between `Serve()` and `Shutdown()`, use **Method 2**:
- Embed `pprof.Lookup("goroutine")` in your test
- Print goroutine stacks if `Serve()` hasn’t returned after shutdown
- Helps detect `Accept()` blocks caused by prematurely closed listeners

---

## Related References

- [Go issue 30333](https://github.com/golang/go/issues/30333)
- [Go http.Server Accept() shutdown hang](https://stackoverflow.com/questions/45751869/http-server-serve-method-hangs-when-calling-shutdown-immediately)
