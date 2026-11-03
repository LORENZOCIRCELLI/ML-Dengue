import { useCallback, useEffect, useState } from 'react';

interface ResourceState<T> {
  key: string;
  data: T | null;
  error: string | null;
}

export function useAsyncResource<T>(key: string, load: () => Promise<T>) {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<ResourceState<T>>({
    key: '',
    data: null,
    error: null,
  });
  const reload = useCallback(() => setAttempt((value) => value + 1), []);

  useEffect(() => {
    let active = true;
    setState({ key, data: null, error: null });
    load().then(
      (data) => {
        if (active) setState({ key, data, error: null });
      },
      (error: unknown) => {
        if (active)
          setState({
            key,
            data: null,
            error:
              error instanceof Error
                ? error.message
                : 'Não foi possível carregar os dados.',
          });
      },
    );
    return () => {
      active = false;
    };
  }, [key, load, attempt]);

  return {
    data: state.key === key ? state.data : null,
    error: state.key === key ? state.error : null,
    reload,
  };
}
