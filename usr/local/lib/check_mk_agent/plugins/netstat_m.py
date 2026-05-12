#!/usr/bin/env python3


import subprocess


def parse_val(s: str) -> int:
	s = s.strip()
	if s.endswith('K'):
		return int(s[:-1]) * 1024
	if s.endswith('M'):
		return int(s[:-1]) * 1024 * 1024
	if s.endswith('G'):
		return int(s[:-1]) * 1024 * 1024 * 1024
	return int(s)


# Short check names mapped to the original descriptions from netstat -m
CHECK_NAMES = {
	"mbufs in use": "MBUF In Use",
	"mbuf clusters in use": "MBUF Clusters In Use",
	"mbuf+clusters out of packet secondary zone in use": "MBUF Packet Secondary Zone",
	"4k (page size) jumbo clusters in use": "MBUF Jumbo 4k",
	"9k jumbo clusters in use": "MBUF Jumbo 9k",
	"16k jumbo clusters in use": "MBUF Jumbo 16k",
	"bytes allocated to network": "MBUF Bytes",
	"requests for mbufs denied": "MBUF Denied",
	"requests for mbufs delayed": "MBUF Delayed",
	"requests for jumbo clusters delayed": "MBUF Jumbo Delayed",
	"requests for jumbo clusters denied": "MBUF Jumbo Denied",
	"sendfile syscalls": "Sendfile Syscalls",
	"sendfile syscalls completed without I/O request": "Sendfile Without I/O",
	"requests for I/O initiated by sendfile": "Sendfile I/O Requests",
	"pages read by sendfile as part of a request": "Sendfile Pages Read",
	"pages were valid at time of a sendfile request": "Sendfile Pages Valid",
	"pages were valid and substituted to bogus page": "Sendfile Pages Bogus",
	"pages were requested for read ahead by applications": "Sendfile Read Ahead Request",
	"pages were read ahead by sendfile": "Sendfile Read Ahead",
	"times sendfile encountered an already busy page": "Sendfile Page Busy",
	"requests for sfbufs denied": "Sendfile Buffer Denied",
	"requests for sfbufs delayed": "Sendfile Buffer Delayed",
}

def parse_line(line: str) -> tuple[dict[str, int], str]:
	parts = line.split(" ", 1)
	values = [parse_val(v) for v in parts[0].split("/")]
	rest = parts[1]

	last_paren = rest.rfind("(")
	if last_paren != -1:
		description = rest[:last_paren].strip()
		keys_str = rest[last_paren + 1:]
		keys = [k.strip() for k in keys_str.rstrip(")").split("/")]
	else:
		description = rest.strip()
		keys = ['active']

	result = {}
	for k, v in zip(keys, values):
		# "current" conflicts with CheckMK's electrical current metric name
		result["active" if k == "current" else k] = v

	return result, description


def output_metric(name: str, kv: dict[str, int], state: int = 0, description: str = "") -> None:
	if not kv:
		return

	  # Build performance data string from key=value pairs
	perf_parts = []
	for k, v in kv.items():
		perf_parts.append(f"{k}={v}")

	# Use description as human-readable summary (the verbose original text)
	active_val = kv.get("active", None)
	if active_val is not None:
		display = f"{active_val} {description}" if description else str(active_val)
	else:
		display = description if description else ", ".join(str(v) for v in kv.values())

	print(f'{state} "{name}" {"|".join(perf_parts)} {display}')


def main() -> None:
	"""Run netstat -m and output CheckMK metrics."""
	result = subprocess.run(
		["netstat", "-m"],
		capture_output=True,
		text=True,
	)

	for line in result.stdout.splitlines():
		if not line.strip():
			continue

		kv, description = parse_line(line)
		if not description or not kv:
			continue

		# Look up short check name
		check_name = CHECK_NAMES.get(description, description)

		values = list(kv.values())

		# Determine state based on whether any value is non-zero for "denied/delayed" metrics
		state = 0
		if any(v != 0 for v in values):
			# If this is a denied/delayed metric, non-zero means warning
			if "denied" in description.lower() or "delayed" in description.lower():
				state = 1

		output_metric(check_name, kv, state, description)


if __name__ == "__main__":
	main()
