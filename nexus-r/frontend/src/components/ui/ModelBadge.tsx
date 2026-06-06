import { useState } from 'react';
import { getModelBrandInfo, CUSTOM_BRAND_ICONS, type BrandInfo } from '../../utils/modelBrandMap';

interface ModelBadgeProps {
  modelId: string;
  size?: number;
  showLabel?: boolean;
  className?: string;
}

const FALLBACK_ICON = 'data:image/svg+xml,' + encodeURIComponent(
  '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#6b7280" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="16" height="10" x="4" y="6" rx="2"/><path d="M12 6V4M8 6V2M16 6V2M9 11h6M9 14h4"/></svg>'
);

export default function ModelBadge({ modelId, size = 18, showLabel = false, className = '' }: ModelBadgeProps) {
  const [imgError, setImgError] = useState(false);
  const brand: BrandInfo = getModelBrandInfo(modelId);

  function renderIcon() {
    // 1. Custom inline SVG (for brands without Simple Icons)
    const customIcon = CUSTOM_BRAND_ICONS[brand.slug];
    if (customIcon) {
      return (
        <img
          src={customIcon}
          alt={brand.label}
          width={size}
          height={size}
          className="shrink-0 rounded-sm"
        />
      );
    }

    // 2. Show fallback if CDN errored or brand is unknown
    if (imgError || brand.slug === 'robot') {
      return (
        <img
          src={FALLBACK_ICON}
          alt={brand.label}
          width={size}
          height={size}
          className={`shrink-0 rounded-sm ${className}`}
          style={{ opacity: 0.5 }}
        />
      );
    }

    // 3. Simple Icons CDN
    const cdnUrl = `https://cdn.simpleicons.org/${brand.slug}/${brand.color}`;
    return (
      <img
        src={cdnUrl}
        alt={brand.label}
        width={size}
        height={size}
        className="rounded-sm"
        onError={() => setImgError(true)}
      />
    );
  }

  return (
    <span
      className={`inline-flex items-center justify-center shrink-0 rounded-sm ${className}`}
      style={{ width: size, height: size }}
    >
      {renderIcon()}
      {showLabel && (
        <span className="ml-1.5 text-xs font-medium" style={{ color: `#${brand.color}` }}>
          {brand.label}
        </span>
      )}
    </span>
  );
}
