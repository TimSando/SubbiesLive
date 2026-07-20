import { useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

export const useGoBack = (fallbackUrl = '/') => {
  const navigate = useNavigate();
  const location = useLocation();

  return useCallback(() => {
    if (location.key !== 'default') {
      navigate(-1);
    } else {
      navigate(fallbackUrl, { replace: true });
    }
  }, [navigate, location, fallbackUrl]);
};
