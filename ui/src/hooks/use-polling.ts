import { useEffect, useRef, useCallback, useState } from "react";

interface UsePollingOptions {
  interval?: number;
  enabled?: boolean;
}

export function usePolling<T>(
  fetcher: () => Promise<T>,
  options: UsePollingOptions = {},
) {
  const { interval = 15000, enabled = true } = options;
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const execute = useCallback(async () => {
    try {
      const result = await fetcherRef.current();
      setData(result);
      setError(null);
      setLoading(false);
      return result;
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
      setLoading(false);
      return null;
    }
  }, []);

  useEffect(() => {
    if (!enabled) return;
    execute();
    const id = setInterval(execute, interval);
    return () => clearInterval(id);
  }, [execute, interval, enabled]);

  return { data, error, loading, refetch: execute };
}
