import { Sun, Cloud, CloudRain, CloudSnow, CloudLightning, CloudDrizzle, CloudFog, Wind } from 'lucide-react';

const WMO_CODES: Record<number, { icon: typeof Sun; label: string }> = {
  0: { icon: Sun, label: 'Clear' },
  1: { icon: Sun, label: 'Mainly clear' },
  2: { icon: Cloud, label: 'Partly cloudy' },
  3: { icon: Cloud, label: 'Overcast' },
  45: { icon: CloudFog, label: 'Foggy' },
  48: { icon: CloudFog, label: 'Depositing rime fog' },
  51: { icon: CloudDrizzle, label: 'Light drizzle' },
  53: { icon: CloudDrizzle, label: 'Moderate drizzle' },
  55: { icon: CloudDrizzle, label: 'Dense drizzle' },
  61: { icon: CloudRain, label: 'Slight rain' },
  63: { icon: CloudRain, label: 'Moderate rain' },
  65: { icon: CloudRain, label: 'Heavy rain' },
  71: { icon: CloudSnow, label: 'Slight snow' },
  73: { icon: CloudSnow, label: 'Moderate snow' },
  75: { icon: CloudSnow, label: 'Heavy snow' },
  80: { icon: CloudRain, label: 'Slight rain showers' },
  81: { icon: CloudRain, label: 'Moderate rain showers' },
  82: { icon: CloudRain, label: 'Violent rain showers' },
  95: { icon: CloudLightning, label: 'Thunderstorm' },
  96: { icon: CloudLightning, label: 'Thunderstorm with slight hail' },
  99: { icon: CloudLightning, label: 'Thunderstorm with heavy hail' },
};

interface WeatherCardProps {
  data: {
    location: string;
    current?: {
      temperature?: number;
      feels_like?: number;
      humidity?: number;
      wind_speed?: number;
      weather_code?: number;
    };
    units?: Record<string, string>;
    error?: string;
  };
}

export default function WeatherCard({ data }: WeatherCardProps) {
  if (data.error) {
    return (
      <div className="px-3 py-2 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg text-xs text-orange-700 dark:text-orange-300">
        {data.error}
      </div>
    );
  }

  const current = data.current;
  if (!current) return null;

  const code = current.weather_code ?? -1;
  const weather = WMO_CODES[code] ?? { icon: Cloud, label: 'Unknown' };
  const Icon = weather.icon;
  const tempUnit = data.units?.temperature_2m ?? '°C';
  const windUnit = data.units?.wind_speed_10m ?? 'km/h';

  return (
    <div className="px-4 py-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800/40 rounded-xl flex items-start gap-4 min-w-[200px]">
      <Icon size={32} className="text-blue-500 dark:text-blue-400 shrink-0 mt-1" />
      <div className="flex-1 min-w-0">
        <div className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
          {data.location}
        </div>
        <div className="text-2xl font-bold text-gray-900 dark:text-gray-100 mt-0.5">
          {current.temperature}{tempUnit}
        </div>
        <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
          {weather.label} &middot; Feels like {current.feels_like}{tempUnit}
        </div>
        <div className="flex gap-3 mt-1.5 text-[11px] text-gray-500 dark:text-gray-400">
          <span>Humidity: {current.humidity}%</span>
          <span className="flex items-center gap-0.5">
            <Wind size={11} />
            {current.wind_speed} {windUnit}
          </span>
        </div>
      </div>
    </div>
  );
}
