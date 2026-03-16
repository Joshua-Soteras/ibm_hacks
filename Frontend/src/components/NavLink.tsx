import { NavLink as RouterNavLink, type NavLinkProps } from "react-router-dom";
import { forwardRef } from "react";
import { cn } from "@/lib/utils";

interface NavLinkCompatProps extends Omit<NavLinkProps, "className"> {
    className?: string | ((props: { isActive: boolean; isPending: boolean }) => string);
    activeClassName?: string;
    pendingClassName?: string;
}

const NavLink = forwardRef<HTMLAnchorElement, NavLinkCompatProps>(
    ({ className, activeClassName, pendingClassName, to, ...props }, ref) => {
        return (
            <RouterNavLink
                ref={ref}
                to={to}
                className={(navProps) => {
                    const baseClass = typeof className === "function" ? className(navProps) : className;
                    return cn(
                        baseClass,
                        navProps.isActive && activeClassName,
                        navProps.isPending && pendingClassName
                    );
                }}
                {...props}
            />
        );
    },
);

NavLink.displayName = "NavLink";

export { NavLink };
