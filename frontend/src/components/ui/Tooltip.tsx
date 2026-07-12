// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0)
//   §Component Standards: reusable design-system component.
// handbook/ui/01_UI_TECHNOLOGY_STANDARD §Component Library: shadcn/ui
//   (Radix primitives) is the FROZEN headless foundation.
// handbook/ui/visual_engineering/05_GLASS_SURFACE_SYSTEM §Tooltips: "Must
//   use Glass, Blur, Rounded corners, Thin border, Small shadow. Never use
//   browser default tooltips." §Floating Glass Surface.
// Per Doc 00 §14.11
'use client'

import { type ReactNode } from 'react'
import * as TooltipPrimitive from '@radix-ui/react-tooltip'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils/cn'

export const TooltipProvider = TooltipPrimitive.Provider

interface TooltipProps {
  content: ReactNode
  children: ReactNode
  side?: 'top' | 'right' | 'bottom' | 'left'
  className?: string
}

// One glass tooltip recipe for the whole app — every `title="..."` browser
// tooltip Doc 05 forbids should route through this instead.
export function Tooltip({ content, children, side = 'top', className }: TooltipProps) {
  return (
    <TooltipPrimitive.Root delayDuration={250}>
      <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content asChild side={side} sideOffset={8} collisionPadding={8}>
          <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.96 }}
            transition={{ duration: 0.12, ease: 'easeOut' }}
            className={cn(
              'z-50 max-w-[240px] rounded-lg border border-border/[0.1] bg-surface-raised/85 px-2.5 py-1.5 text-caption text-fg shadow-lg backdrop-blur-xl',
              className,
            )}
          >
            {content}
            <TooltipPrimitive.Arrow className="fill-surface-raised" />
          </motion.div>
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  )
}
