"use client";

import ReactMarkdown, { defaultUrlTransform } from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";

/** Styled markdown renderer used for assistant messages. */
export function Markdown({ children, className }: { children: string; className?: string }) {
  return (
    <div
      className={cn(
        "prose-fp max-w-none text-[15px] leading-relaxed",
        "[&_p]:my-2 [&_p:first-child]:mt-0 [&_p:last-child]:mb-0",
        "[&_strong]:font-semibold [&_strong]:text-foreground",
        "[&_a]:text-brand-600 [&_a]:underline [&_a]:underline-offset-2 dark:[&_a]:text-brand-300",
        "[&_code]:rounded-md [&_code]:bg-muted [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:text-[13px] [&_code]:font-medium",
        "[&_ul]:my-2 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:my-2 [&_ol]:list-decimal [&_ol]:pl-5 [&_li]:my-0.5",
        "[&_h1]:font-display [&_h2]:font-display [&_h3]:font-display [&_h1]:text-xl [&_h2]:text-lg [&_h3]:text-base [&_h2]:mt-3 [&_h2]:mb-1",
        "[&_blockquote]:border-l-2 [&_blockquote]:border-brand-500/50 [&_blockquote]:pl-3 [&_blockquote]:text-muted-foreground",
        "[&_pre]:my-2 [&_pre]:overflow-x-auto [&_pre]:rounded-xl [&_pre]:bg-foreground/5 [&_pre]:p-3",
        "[&_table]:my-2 [&_table]:w-full [&_table]:text-sm [&_th]:border-b [&_th]:border-border [&_th]:py-1 [&_th]:text-left [&_td]:border-b [&_td]:border-border/60 [&_td]:py-1",
        className
      )}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        // Allow tel: links (react-markdown strips non-http(s) URLs by default),
        // so the "call the restaurant" links work.
        urlTransform={(url) => (url.startsWith("tel:") ? url : defaultUrlTransform(url))}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
