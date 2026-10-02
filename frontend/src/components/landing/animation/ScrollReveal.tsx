
import {
  type HTMLMotionProps,
  motion,
  useReducedMotion,
  type Variants,
} from "motion/react";
import type { ReactNode } from "react";

type Direction = "up" | "down" | "left" | "right" | "none";

// Framer signature smooth cubic-bezier easing curve
const FRAMER_EASE = [0.22, 1, 0.36, 1] as const;

interface ScrollRevealProps extends HTMLMotionProps<"div"> {
  children: ReactNode;
  direction?: Direction;
  distance?: number;
  duration?: number;
  delay?: number;
  scale?: boolean;
  once?: boolean;
  className?: string;
}

export function ScrollReveal({
  children,
  direction = "up",
  distance = 24,
  duration = 1.05,
  delay = 0,
  scale = false,
  once = true,
  className,
  ...props
}: ScrollRevealProps) {
  const reduceMotion = useReducedMotion();

  const getOffset = () => {
    switch (direction) {
      case "up":
        return { y: distance, x: 0 };
      case "down":
        return { y: -distance, x: 0 };
      case "left":
        return { x: distance, y: 0 };
      case "right":
        return { x: -distance, y: 0 };
      default:
        return { x: 0, y: 0 };
    }
  };

  const offset = reduceMotion ? { x: 0, y: 0 } : getOffset();

  return (
    <motion.div
      initial={{
        opacity: reduceMotion ? 1 : 0,
        x: offset.x,
        y: offset.y,
        scale: reduceMotion || !scale ? 1 : 0.98,
      }}
      whileInView={{
        opacity: 1,
        x: 0,
        y: 0,
        scale: 1,
      }}
      viewport={{
        once,
        amount: 0.05,
        margin: "0px 0px 0px 0px",
      }}
      transition={{
        duration: reduceMotion ? 0 : duration,
        delay: reduceMotion ? 0 : delay,
        ease: FRAMER_EASE,
      }}
      className={className}
      {...props}
    >
      {children}
    </motion.div>
  );
}

interface StaggerContainerProps extends HTMLMotionProps<"div"> {
  children: ReactNode;
  staggerDelay?: number;
  delayChildren?: number;
  once?: boolean;
  amount?: number;
  className?: string;
}

export function StaggerContainer({
  children,
  staggerDelay = 0.12,
  delayChildren = 0,
  once = true,
  amount = 0.15,
  className,
  ...props
}: StaggerContainerProps) {
  const reduceMotion = useReducedMotion();

  const containerVariants: Variants = {
    hidden: {},
    visible: {
      transition: {
        staggerChildren: reduceMotion ? 0 : staggerDelay,
        delayChildren: reduceMotion ? 0 : delayChildren,
      },
    },
  };

  return (
    <motion.div
      initial="hidden"
      whileInView="visible"
      viewport={{ once, amount, margin: "0px 0px -40px 0px" }}
      variants={containerVariants}
      className={className}
      {...props}
    >
      {children}
    </motion.div>
  );
}

interface StaggerItemProps extends HTMLMotionProps<"div"> {
  children: ReactNode;
  direction?: Direction;
  distance?: number;
  duration?: number;
  scale?: boolean;
  className?: string;
}

export function StaggerItem({
  children,
  direction = "up",
  distance = 20,
  duration = 0.95,
  scale = false,
  className,
  ...props
}: StaggerItemProps) {
  const reduceMotion = useReducedMotion();

  const getOffset = () => {
    switch (direction) {
      case "up":
        return { y: distance, x: 0 };
      case "down":
        return { y: -distance, x: 0 };
      case "left":
        return { x: distance, y: 0 };
      case "right":
        return { x: -distance, y: 0 };
      default:
        return { x: 0, y: 0 };
    }
  };

  const offset = reduceMotion ? { x: 0, y: 0 } : getOffset();

  const itemVariants: Variants = {
    hidden: {
      opacity: reduceMotion ? 1 : 0,
      x: offset.x,
      y: offset.y,
      scale: reduceMotion || !scale ? 1 : 0.98,
    },
    visible: {
      opacity: 1,
      x: 0,
      y: 0,
      scale: 1,
      transition: {
        duration: reduceMotion ? 0 : duration,
        ease: FRAMER_EASE,
      },
    },
  };

  return (
    <motion.div variants={itemVariants} className={className} {...props}>
      {children}
    </motion.div>
  );
}
