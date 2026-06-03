import { Tooltip } from './Tooltip';

export function ComingSoonBadge() {
  return (
    <Tooltip content="This feature is planned for a future release." position="top">
      <div className="inline-block cursor-default">
        <span 
          className="inline-flex items-center justify-center min-w-[100px] py-[8px] px-[12px] rounded-full text-[12px] leading-none font-semibold uppercase tracking-[0.5px] whitespace-nowrap bg-[#FEF3C7] border border-[#F59E0B] text-[#92400E] dark:bg-[rgba(245,158,11,0.15)] dark:border-[#F59E0B] dark:text-[#FBBF24]"
        >
          COMING SOON
        </span>
      </div>
    </Tooltip>
  );
}
