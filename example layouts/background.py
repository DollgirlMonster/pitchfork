"""
    Slide with a backgroung image
"""

def match(slide) -> bool:
    # Claim slides that have a ::background:: zone
    return "background" in slide.zones


def html(slide, md) -> str:
    body = md(slide.content)
    background_img = slide.zones.get("background", "")
    
    return (
        '<div class="slide-layout body custom-bg">' +
        '<div class="background-image" style="background-image: url(\'' + background_img + '\');"></div>' +
        '<div class="background-overlay"></div>' +
        '<div class="content-wrapper">' +
        body +
        '</div>' +
        '</div>'
    )


"""

CSS for styles.css:

.slide-layout.body.custom-bg {
  position: relative;
  overflow: hidden;

  .background-image {
    position: absolute;
    inset: 0;
    background-size: cover;
    background-position: center;
    z-index: -2;
  }

  .background-overlay {
    position: absolute;
    inset: 0;
    background: black;
    opacity: 0.3;
    z-index: -1;
  }

  .content-wrapper {
    position: relative;
    z-index: 1;
  }

  h1, h2, h3, h4, h5, h6, p, strong, em {
    color: var(--pf-fg);
  }
}

"""