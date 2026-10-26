import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Summary as SummaryProps } from "./summary.types";

const Summary = ({summary}: SummaryProps) => {
    return(
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {summary}
        </ReactMarkdown>
    )
}
export default Summary;