import WeatherCard from './WeatherCard';
import CalculatorCard from './CalculatorCard';
import CitationCard from './CitationCard';
import StockCard from './StockCard';
import RouterDecisionCard from './RouterDecisionCard';
import ModelStatusCard from './ModelStatusCard';
import MemoryCard from './MemoryCard';
import CostAnalyticsCard from './CostAnalyticsCard';

interface WidgetData {
  type: string;
  data: any;
  title?: string;
}

interface WidgetDispatcherProps {
  widget: WidgetData;
}

export default function WidgetDispatcher({ widget }: WidgetDispatcherProps) {
  switch (widget.type) {
    case 'weather':
      return <WeatherCard data={widget.data} />;
    case 'calculator':
      return <CalculatorCard data={widget.data} />;
    case 'citation':
      return <CitationCard data={widget.data} />;
    case 'stock':
      return <StockCard data={widget.data} />;
    case 'router_decision':
      return <RouterDecisionCard data={widget.data} />;
    case 'model_status':
      return <ModelStatusCard data={widget.data} />;
    case 'memory':
      return <MemoryCard data={widget.data} />;
    case 'cost_analytics':
      return <CostAnalyticsCard data={widget.data} />;
    default:
      return null;
  }
}
