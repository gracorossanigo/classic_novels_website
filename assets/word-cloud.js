(function () {
  'use strict';

  const DATA = [
    { text: 'The Great Gatsby',                        count: 6 },
    { text: 'Anna Karenina',                           count: 5 },
    { text: 'Brave New World',                         count: 5 },
    { text: 'Jane Eyre',                               count: 5 },
    { text: 'Little Women',                            count: 5 },
    { text: 'Madame Bovary',                           count: 5 },
    { text: 'Moby Dick',                               count: 5 },
    { text: 'Pride and Prejudice',                     count: 5 },
    { text: 'The Catcher in the Rye',                  count: 5 },
    { text: 'To Kill a Mockingbird',                   count: 5 },
    { text: 'Ulysses',                                 count: 5 },
    { text: 'Wuthering Heights',                       count: 5 },
    { text: 'Catch-22',                                count: 4 },
    { text: 'Crime and Punishment',                    count: 4 },
    { text: 'Don Quixote',                             count: 4 },
    { text: 'Frankenstein',                            count: 4 },
    { text: 'Great Expectations',                      count: 4 },
    { text: 'Lolita',                                  count: 4 },
    { text: 'Mrs. Dalloway',                           count: 4 },
    { text: 'One Hundred Years of Solitude',           count: 4 },
    { text: 'The Adventures of Huckleberry Finn',      count: 4 },
    { text: 'The Call of the Wild',                    count: 4 },
    { text: 'The Count of Monte Cristo',               count: 4 },
    { text: 'The Grapes of Wrath',                     count: 4 },
    { text: 'The Lord of the Rings',                   count: 4 },
    { text: 'The Picture of Dorian Gray',              count: 4 },
    { text: 'The Wind in the Willows',                 count: 4 },
    { text: 'Things Fall Apart',                       count: 4 },
    { text: 'A Portrait of the Artist as a Young Man', count: 3 },
    { text: "Alice's Adventures in Wonderland",        count: 3 },
    { text: 'As I Lay Dying',                          count: 3 },
    { text: 'Beloved',                                 count: 3 },
    { text: 'Bleak House',                             count: 3 },
    { text: "Charlotte's Web",                         count: 3 },
    { text: 'Dracula',                                 count: 3 },
    { text: 'In Cold Blood',                           count: 3 },
    { text: "Lady Chatterley's Lover",                 count: 3 },
    { text: 'Les Misérables',                          count: 3 },
    { text: 'Lord of the Flies',                       count: 3 },
    { text: 'Middlemarch',                             count: 3 },
    { text: 'On the Road',                             count: 3 },
    { text: 'Orlando',                                 count: 3 },
    { text: 'Song of Solomon',                         count: 3 },
    { text: "Tess of the d'Urbervilles",               count: 3 },
    { text: 'The Age of Innocence',                    count: 3 },
    { text: 'The Jungle',                              count: 3 },
    { text: 'The Mill on the Floss',                   count: 3 },
    { text: 'The Portrait of a Lady',                  count: 3 },
    { text: 'The Scarlet Letter',                      count: 3 },
    { text: 'The Trial',                               count: 3 },
    { text: 'To the Lighthouse',                       count: 3 },
    { text: 'Tropic of Cancer',                        count: 3 },
    { text: 'Wide Sargasso Sea',                       count: 3 },
    { text: 'A Christmas Carol',                       count: 2 },
    { text: 'A Farewell to Arms',                      count: 2 },
    { text: 'A Passage to India',                      count: 2 },
    { text: 'A Tale of Two Cities',                    count: 2 },
    { text: 'Animal Farm',                             count: 2 },
    { text: 'Atlas Shrugged',                          count: 2 },
    { text: 'Black Beauty',                            count: 2 },
    { text: 'Brideshead Revisited',                    count: 2 },
    { text: 'Fahrenheit 451',                          count: 2 },
    { text: 'For Whom the Bell Tolls',                 count: 2 },
    { text: "Giovanni's Room",                         count: 2 },
    { text: 'Gone with the Wind',                      count: 2 },
    { text: "Gulliver's Travels",                      count: 2 },
    { text: 'Heart of Darkness',                       count: 2 },
    { text: 'Housekeeping',                            count: 2 },
    { text: 'In Search of Lost Time',                  count: 2 },
    { text: 'Kidnapped',                               count: 2 },
    { text: 'Lord Jim',                                count: 2 },
    { text: "Midnight's Children",                     count: 2 },
    { text: 'My Ántonia',                              count: 2 },
    { text: 'Native Son',                              count: 2 },
    { text: 'Of Mice and Men',                         count: 2 },
    { text: "One Flew Over the Cuckoo's Nest",         count: 2 },
    { text: 'Peter Pan',                               count: 2 },
    { text: "Pilgrim's Progress",                      count: 2 },
    { text: 'Scoop',                                   count: 2 },
    { text: 'Sense and Sensibility',                   count: 2 },
    { text: 'Slaughterhouse-Five',                     count: 2 },
    { text: 'Sons and Lovers',                         count: 2 },
    { text: 'The Awakening',                           count: 2 },
    { text: 'The Brothers Karamazov',                  count: 2 },
    { text: 'The Color Purple',                        count: 2 },
    { text: "The French Lieutenant's Woman",           count: 2 },
    { text: "The Handmaid's Tale",                     count: 2 },
    { text: 'The Hunchback of Notre-Dame',             count: 2 },
    { text: 'The Invisible Man',                       count: 2 },
    { text: 'The Master and Margarita',                count: 2 },
    { text: 'The Old Man and the Sea',                 count: 2 },
    { text: 'The Quiet American',                      count: 2 },
    { text: 'The Return of the Native',                count: 2 },
    { text: 'The Secret Garden',                       count: 2 },
    { text: 'The Secret History',                      count: 2 },
    { text: 'The Stranger',                            count: 2 },
    { text: 'The Sun Also Rises',                      count: 2 },
    { text: 'The Time Machine',                        count: 2 },
    { text: 'The Wonderful Wizard of Oz',              count: 2 },
    { text: 'Their Eyes Were Watching God',            count: 2 },
    { text: "Uncle Tom's Cabin",                       count: 2 },
    { text: 'War and Peace',                           count: 2 },
    { text: 'A Clockwork Orange',                      count: 1 },
    { text: 'East of Eden',                            count: 1 },
    { text: 'Finnegans Wake',                          count: 1 },
    { text: 'The Bell Jar',                            count: 1 },
    { text: 'The Hobbit',                              count: 1 },
    { text: 'The Three Musketeers',                    count: 1 },
  ];

  const BASE_SIZES = [9, 12, 15, 20, 26, 34];
  const BASE_DIM = 520;

  function fontSize(count, scale) {
    return BASE_SIZES[count - 1] * scale;
  }

  function fillColor(count) {
    if (count >= 5) return '#74a7f8';
    if (count >= 3) return '#60a5fa';
    return '#93c5fd';
  }

  function fillOpacity(count) {
    if (count >= 5) return 0.75;
    if (count >= 3) return 0.55;
    return 0.4;
  }

  function init() {
    const el = document.getElementById('word-cloud');
    if (!el) return;
    if (typeof d3 === 'undefined' || !d3.layout || !d3.layout.cloud) return;

    document.fonts.ready.then(function () {
      const W = el.offsetWidth || BASE_DIM;
      const H = el.offsetHeight || BASE_DIM;
      const scale = W / BASE_DIM;

      const words = DATA.map(function (d) {
        return { text: d.text, count: d.count, size: fontSize(d.count, scale) };
      });

      d3.layout.cloud()
        .size([W, H])
        .words(words)
        .padding(1)
        .spiral('rectangular')
        .rotate(function () { return Math.random() < 0.35 ? 90 : 0; })
        .font("'DM Serif Display', Georgia, serif")
        .fontStyle('normal')
        .fontSize(function (d) { return d.size; })
        .on('end', function (placed) {
          const svg = d3.select(el)
            .append('svg')
            .attr('width', W)
            .attr('height', H);

          svg.append('g')
            .attr('transform', 'translate(' + W / 2 + ',' + H / 2 + ')')
            .selectAll('text')
            .data(placed)
            .enter()
            .append('text')
            .style('font-size', function (d) { return d.size + 'px'; })
            .style('font-family', "'DM Serif Display', Georgia, serif")
            .style('font-style', 'normal')
            .style('fill', function (d) { return fillColor(d.count); })
            .style('opacity', function (d) { return fillOpacity(d.count); })
            .attr('text-anchor', 'middle')
            .attr('transform', function (d) {
              return 'translate(' + d.x + ',' + d.y + ')rotate(' + d.rotate + ')';
            })
            .text(function (d) { return d.text; });
        })
        .start();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
