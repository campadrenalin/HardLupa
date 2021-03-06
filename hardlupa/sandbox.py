import multiprocessing
from runtime import HardRuntime

class Sandbox(object):
    # An isolated process that handles a pool of runtimes.
    def __init__(self):
        self.parent_conn, self.child_conn = multiprocessing.Pipe()
        self.process = multiprocessing.Process(
            target=self.run,
            args=(
				self.child_conn,
			),
		)
        self.process.daemon = True
        self.process.start()

    def run(self, conn):
        self.runtimes = {}
        self.closed = False
        while not self.closed:
            call, args, kwargs = self.recv(conn)
            try:
                getattr(self, "_"+call)(conn, *args, **kwargs)
            except Exception as e:
                self.send(conn, e)

    def send(self, conn, value):
        if self.process.is_alive():
            conn.send(value)
        else:
            raise IOError("Process is dead.")

    def recv(self, conn, timeout=0):
        if self.process.is_alive():
            return conn.recv()
        else:
            raise IOError("Process is dead.")

    def call(self, name, args, kwargs, timeout=0):
        self.send(self.parent_conn, (name, args, kwargs))
        return self.recv(self.parent_conn)

    def _create_runtime(self, conn, name=None):
        # Create and return a handle to a runtime
        if (name==None):
            name = "auto_"+str(len(self.runtimes))
        self.runtimes[name] = HardRuntime()
        self.send(conn, name) 

    def _execute(self, conn, name, code):
        # Execute lua code in a runtime
        self.send(conn,
            self.runtimes[name].execute(code)
        )

    def _eval(self, conn, name, code):
        # Execute lua code in a runtime
        self.send(conn,
            self.runtimes[name].eval(code)
        )

    def _globals(self, conn, name):
        self.send(conn,
            self.runtimes[name].globals
        )

    def _close(self, conn):
        # Terminate the sandbox process
        self.closed = True
        self.send(conn, "HardLupa sandbox is terminating...")

    def create_runtime(self, name=None):
        return SBRuntime(
            self,
            self.call("create_runtime", (), {'name':name}),
        )

    def execute(self, name, code):
        return self.call("execute", (name, code), {})

    def eval(self, name, code):
        return self.call("eval", (name, code), {})

    def globals(self, name):
        return self.call("globals", (name,), {})

    def close(self):
        return self.call("close", (), {})


class SBRuntime(object):
    def __init__(self, sandbox, name):
        self.sandbox = sandbox
        self.name    = name

    def execute(self, code):
        return self.sandbox.execute(self.name, code)

    def eval(self, code):
        return self.sandbox.eval(self.name, code)

    def __getitem__(self, i):
        return self.eval(i)

    @property
    def globals(self):
        return self.sandbox.globals(self.name)
