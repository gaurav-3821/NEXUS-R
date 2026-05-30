import { Badge } from './Badge';
import { Tooltip } from './Tooltip';

export function ComingSoonBadge() {
  return (
    <Tooltip content="This feature is planned for a future release." position="top">
      <div className="inline-block cursor-not-allowed">
        <Badge variant="secondary" className="opacity-70">
          Coming Soon
        </Badge>
      </div>
    </Tooltip>
  );
}
